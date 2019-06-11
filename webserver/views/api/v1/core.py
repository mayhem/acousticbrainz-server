from __future__ import absolute_import

import json
import uuid

from flask import Blueprint, request, jsonify

import db.data
import webserver.views.api.exceptions
from db.data import submit_low_level_data, count_lowlevel
from db.exceptions import NoDataFoundException, BadDataException
from webserver.decorators import crossdomain
from utils.remove_duplicates import remove_duplicates

bp_core = Blueprint('api_v1_core', __name__)


# If this value is increased, ensure that it still fits within the uwsgi header size:
# https://uwsgi-docs.readthedocs.io/en/latest/ThingsToKnow.html
# > By default uWSGI allocates a very small buffer (4096 bytes) for the headers of each request.
# > If you start receiving "invalid request block size" in your logs, it could mean you need a bigger buffer.
# > Increase it (up to 65535) with the buffer-size option.

#: The maximum number of items that you can pass as a recording_ids parameter to bulk lookup endpoints
MAX_ITEMS_PER_BULK_REQUEST = 25
# Individual features selectable in get_many_select_features.
# Note: metadata.version and metadata.audio_properties will be included in all responses.
SELECTABLE_FEATURES = {"lowlevel.average_loudness": "llj.data->'lowlevel'->'average_loudness'", 
                        "lowlevel.dynamic_complexity": "llj.data->'lowlevel'->'dynamic_complexity'", 
                        "metadata.audio_properties.replay_gain": "llj.data->'metadata'->'audio_properties'->'replay_gain'",
                        "metadata.tags": "llj.data->'metadata'->'tags'", 
                        "rhythm.beats_count": "llj.data->'rhythm'->'beats_count'", 
                        "rhythm.beats_loudness.mean": "llj.data->'rhythm'->'beats_loudness'->'mean'", 
                        "rhythm.bpm": "llj.data->'rhythm'->'bpm'", 
                        "rhythm.bpm_histogram_first_peak_bpm.mean": "llj.data->'bpm_histogram_first_peak_bpm'->'mean'", 
                        "rhythm.bpm_histogram_second_peak_bpm.mean": "llj.data->'bpm_histogram_second_peak_bpm'->'mean'", 
                        "rhythm.danceability": "llj.data->'rhythm'->'danceability'", 
                        "rhythm.onset_rate": "llj.data->'rhythm'->'onset_rate'", 
                        "tonal.chords_key": "llj.data->'tonal'->'chords_key'", 
                        "tonal.chords_scale": "llj.data->'tonal'->'chords_scale'", 
                        "tonal.key_key": "llj.data->'tonal'->'key_key'", 
                        "tonal.key_scale": "llj.data->'tonal'->'key_scale'", 
                        "tonal.tuning_frequency": "llj.data->'tonal'->'tuning_frequency'", 
                        "tonal.tuning_equal_tempered_deviation": "llj.data->'tonal'->'tuning_equal_tempered_deviation'"}


@bp_core.route("/<uuid:mbid>/count", methods=["GET"])
@crossdomain()
def count(mbid):
    """Get the number of low-level data submissions for a recording with a
    given MBID.

    :resheader Content-Type: *application/json*
    """
    return jsonify({
        'mbid': mbid,
        'count': count_lowlevel(str(mbid)),
    })


@bp_core.route("/<uuid:mbid>/low-level", methods=["GET"])
@crossdomain()
def get_low_level(mbid):
    """Get low-level data for a recording with a given MBID.

    This endpoint returns one document at a time. If there are many submissions
    for an MBID, you can browse through them by specifying an offset parameter
    ``n``. Documents are sorted by their submission time.

    You can the get total number of low-level submissions using the ``/<mbid>/count``
    endpoint.

    :query n: *Optional.* Integer specifying an offset for a document.

    :resheader Content-Type: *application/json*
    """
    offset = _validate_offset(request.args.get("n"))
    try:
        return jsonify(db.data.load_low_level(str(mbid), offset))
    except NoDataFoundException:
        raise webserver.views.api.exceptions.APINotFound("Not found")


@bp_core.route("/<uuid:mbid>/high-level", methods=["GET"])
@crossdomain()
def get_high_level(mbid):
    """Get high-level data for recording with a given MBID.

    This endpoint returns one document at a time. If there are many submissions
    for an MBID, you can browse through them by specifying an offset parameter
    ``n``. Documents are sorted by the submission time of their associated
    low-level documents.

    You can get the total number of low-level submissions using ``/<mbid>/count``
    endpoint.

    :query n: *Optional.* Integer specifying an offset for a document.

    :resheader Content-Type: *application/json*
    """
    offset = _validate_offset(request.args.get("n"))
    try:
        return jsonify(db.data.load_high_level(str(mbid), offset))
    except NoDataFoundException:
        raise webserver.views.api.exceptions.APINotFound("Not found")


@bp_core.route("/<uuid:mbid>/low-level", methods=["POST"])
def submit_low_level(mbid):
    """Submit low-level data to AcousticBrainz.

    :reqheader Content-Type: *application/json*

    :resheader Content-Type: *application/json*
    """
    raw_data = request.get_data()
    try:
        data = json.loads(raw_data.decode("utf-8"))
    except ValueError as e:
        raise webserver.views.api.exceptions.APIBadRequest("Cannot parse JSON document: %s" % e)

    try:
        submit_low_level_data(str(mbid), data, 'mbid')
    except BadDataException as e:
        raise webserver.views.api.exceptions.APIBadRequest("%s" % e)
    return jsonify({"message": "ok"})


def _validate_offset(offset):
    """Validate the offset.

    If the offset is None, return 0, otherwise interpret it as a number. If it is
    not a number, raise 400.
    """
    if offset:
        try:
            offset = int(offset)
        except ValueError:
            raise webserver.views.api.exceptions.APIBadRequest("Offset must be an integer value")
    else:
        offset = 0
    return offset


def _parse_bulk_params(params):
    """Validate and parse a bulk query parameter string.

    A valid parameter string takes the form
      mbid[:offset];mbid[:offset];...
    Where offset is a number >=0. Offsets are optional.
    mbid must be a UUID.

    If an offset is not specified or is invalid, 0 is used as a default.
    If an mbid is not valid, an APIBadRequest Exception is
    raised listing the bad MBID and no further processing is done.

    Returns a list of tuples (mbid, offset)
    """

    ret = []

    for recording in params.split(";"):
        parts = str(recording).split(":")
        recording_id = parts[0]
        try:
            uuid.UUID(recording_id)
        except ValueError:
            raise webserver.views.api.exceptions.APIBadRequest("'%s' is not a valid UUID" % recording_id)
        if len(parts) > 2:
            raise webserver.views.api.exceptions.APIBadRequest("More than 1 : in '%s'" % recording)
        elif len(parts) == 2:
            try:
                offset = int(parts[1])
                # Don't allow negative offsets
                offset = max(offset, 0)
            except ValueError:
                offset = 0
        else:
            offset = 0

        ret.append((recording_id, offset))

    # Remove duplicates, preserving order
    return remove_duplicates(ret)


def check_bad_request_for_multiple_recordings():
    """
    Check if a request for multiple recording ids is valid. The ?recording_ids parameter
    to the current flask request is checked to see if it is present and if it follows
    the format
        mbid:n;mbid:n
    where mbid is a recording MBID and n is an optional integer offset. If the offset is
    missing or non-integer, it is replaced with 0

    Returns:
        a list of (mbid, offset) tuples representing the parsed query string.

    Raises:
        APIBadRequest if there is no recording_ids parameter, there are more than 25 MBIDs in the parameter,
        or the format of the mbids or offsets are invalid
    """
    recording_ids = request.args.get("recording_ids")

    if not recording_ids:
        raise webserver.views.api.exceptions.APIBadRequest("Missing `recording_ids` parameter")

    recordings = _parse_bulk_params(recording_ids)
    if len(recordings) > MAX_ITEMS_PER_BULK_REQUEST:
        raise webserver.views.api.exceptions.APIBadRequest("More than %s recordings not allowed per request" % MAX_ITEMS_PER_BULK_REQUEST)

    return recordings


@bp_core.route("/low-level", methods=["GET"])
@crossdomain()
def get_many_lowlevel():
    """Get low-level data for many recordings at once.

    **Example response**:

    .. sourcecode:: json

       {"mbid1": {"offset1": {document},
                  "offset2": {document}},
        "mbid2": {"offset1": {document}}
       }

    MBIDs and offset keys are returned as strings (as per JSON encoding rules).
    If an offset is not specified in the request for an mbid or is not a valid integer >=0,
    the offset will be 0.

    If the list of MBIDs in the query string has a recording which is not
    present in the database, then it is silently ignored and will not appear
    in the returned data.

    :query recording_ids: *Required.* A list of recording MBIDs to retrieve

      Takes the form `mbid[:offset];mbid[:offset]`. Offsets are optional, and should
      be >= 0

      You can specify up to :py:const:`~webserver.views.api.v1.core.MAX_ITEMS_PER_BULK_REQUEST` MBIDs in a request.

    :resheader Content-Type: *application/json*
    """
    recordings = check_bad_request_for_multiple_recordings()
    recording_details = db.data.load_many_low_level(recordings)

    return jsonify(recording_details)


@bp_core.route("/high-level", methods=["GET"])
@crossdomain()
def get_many_highlevel():
    """Get high-level data for many recordings at once.
    
    **Example response**:

    .. sourcecode:: json

       {"mbid1": {"offset1": {document},
                  "offset2": {document}},
        "mbid2": {"offset1": {document}}
       }

    MBIDs and offset keys are returned as strings (as per JSON encoding rules).
    If an offset is not specified in the request for an mbid or is not a valid integer >=0,
    the offset will be 0.

    If the list of MBIDs in the query string has a recording which is not
    present in the database, then it is silently ignored and will not appear
    in the returned data.

    :query recording_ids: *Required.* A list of recording MBIDs to retrieve

      Takes the form `mbid[:offset];mbid[:offset]`. Offsets are optional, and should
      be >= 0

      You can specify up to :py:const:`~webserver.views.api.v1.core.MAX_ITEMS_PER_BULK_REQUEST` MBIDs in a request.

    :resheader Content-Type: *application/json*
    """
    recordings = check_bad_request_for_multiple_recordings()
    recording_details = db.data.load_many_high_level(recordings)
    
    return jsonify(recording_details)


def parse_select_features():
    """Check whether the features are found or not.
    Parse the query string of features to create a list of 
    the json paths to features, excluding those that are 
    not offered.

    If features are missing, an APIBadRequest Exception is
    raised stating the missing features message.
    
    Returns a string of feature paths with alias:
        "llj.data->'feature1' AS feature1, ..., llj.data->'featureN' AS featureN"
    """
    features_param = request.args.get("features")
    if not features_param:
        raise webserver.views.api.exceptions.APIBadRequest("Missing `features` parameter")

    parsed_features = []
    aliases = []
    for feature in features_param.split(';'):
        if feature in SELECTABLE_FEATURES:
            aliases.append(feature)
            # Build feature path
            feature_path = SELECTABLE_FEATURES[feature]
            parsed_features.append(feature_path)

    # Always include metadata.version and metadata.audio_properties
    metadata_version = "llj.data->'metadata'->'version'"
    metadata_version_alias = "metadata.version"
    metadata_audio_properties = "llj.data->'metadata'->'audio_properties'"
    metadata_audio_properties_alias = "metadata.audio_properties"
    
    parsed_features.append(metadata_version)
    parsed_features.append(metadata_audio_properties)
    aliases.append(metadata_version_alias)
    aliases.append(metadata_audio_properties_alias)

    # Remove duplicates, preserving order
    parsed_features = remove_duplicates(parsed_features)
    return parsed_features, aliases


@bp_core.route("/low-level/select", methods=["GET"])
@crossdomain()
def get_many_select_features():
    """Get a specified subset of low-level data for many recordings at once.
    
    **Example response**:

    .. sourcecode:: json
       {"mbid1": {"offset1": {document},
                  "offset2": {document}},
        "mbid2": {"offset1": {document}}
       }
    
    :query recording_ids: *Required.* A list of recording MBIDs to retrieve.
        
        Takes the form `mbid[:offset];mbid[:offset]`. Offsets are optional, and should
        be >= 0
    
    :query features: *Required.* A list of features to be returned for each mbid.
        
        Takes the form `feature1;feature2`.
    
    :resheader Content-Type: *application/json*
    """
    recordings = check_bad_request_for_multiple_recordings()
    parsed_features, aliases = parse_select_features()
    recording_details = db.data.load_many_select_features(recordings, parsed_features, aliases)

    return jsonify(recording_details)


@bp_core.route("/count", methods=["GET"])
@crossdomain()
def get_many_count():
    """Get low-level count for many recordings at once. MBIDs not found in
    the database are omitted in the response.

    **Example response**:

    .. sourcecode:: json

       {"mbid1": {"count": 3},
        "mbid2": {"count": 1}
       }

    :query recording_ids: *Required.* A list of recording MBIDs to retrieve

      Takes the form `mbid;mbid`.

    You can specify up to :py:const:`~webserver.views.api.v1.core.MAX_ITEMS_PER_BULK_REQUEST` MBIDs in a request.

    :resheader Content-Type: *application/json*
    """
    recordings = check_bad_request_for_multiple_recordings()

    mbids = [mbid for (mbid, offset) in recordings]
    return jsonify(db.data.count_many_lowlevel(mbids))
