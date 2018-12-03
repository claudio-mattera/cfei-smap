import logging
import jsonschema
import json
import pkgutil

import typing


def parse_and_validate(
            text: typing.Text,
            schema_name: typing.Text,
            loose_validation: bool,
        ) -> typing.Any:
    """
    Parse and validate JSON payload

    The JSON schema is loaded from the package's content and used to validate
    the JSON payload.

    :param text: JSON payload.
    :type text: str
    :param schema_name: JSON schema to use for validation.
    :type schema_name: str
    :param loose_validation: If True only logs a warning in case of invalid data.
    :type loose_validation: bool

    :returns: Parsed data structure.
    :rtype: obj

    :raises ValidationError: If the payload does not follow the schema.
    :raises SchemaError: If the schema is not valid.
    """
    logger = logging.getLogger(__name__)

    payload = json.loads(text)

    schema_file_name = schema_name + '.json'
    schema_bytes = pkgutil.get_data(__name__, schema_file_name)
    if schema_bytes is not None:
        schema = json.loads(schema_bytes.decode('utf-8'))
        try:
            jsonschema.validate(
                payload,
                schema,
                format_checker=jsonschema.FormatChecker()
            )
        except jsonschema.exceptions.ValidationError as e:
            if loose_validation:
                logger.warn("Cannot validate JSON: %s", e)
            else:
                raise
        except jsonschema.exceptions.SchemaError as e:
            if loose_validation:
                logger.warn("Invalid JSON schema: %s", e)
            else:
                raise

    return payload
