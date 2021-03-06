import json
import jsonschema
from pyld import jsonld

from ..actions.tasks import add_task
from ..exceptions import TaskPrerequisitesError
from ..extensions import ALL_KNOWN_EXTENSIONS
from ..openbadges_context import OPENBADGES_CONTEXT_V2_DICT
from ..state import get_node_by_id, get_node_by_path
from ..utils import list_of

from .task_types import VALIDATE_EXTENSION_NODE
from .utils import abbreviate_value, is_iri, filter_tasks, task_result


def _validate_single_extension(node, extension_type, node_json=None):
    # Load extension
    extension = ALL_KNOWN_EXTENSIONS[extension_type]

    # Establish node structure to test
    if node_json:
        node_data = json.loads(node_json)
    else:
        node_data = node.copy()

    # Validate against JSON-schema
    context = extension.context_json
    for validation in context.get('obi:validation', []):
        schema_url = validation.get('obi:validationSchema', '')
    schema = extension.validation_schema[schema_url]

    node_data['@context'] = OPENBADGES_CONTEXT_V2_DICT
    compact_data = jsonld.compact(node_data, [OPENBADGES_CONTEXT_V2_DICT, context])

    try:
        jsonschema.validate(compact_data, schema)
    except jsonschema.ValidationError as e:
        return task_result(
            False, "Extension {} did not validate on node {}: {}".format(
                extension_type, node.get('id'), e.message
            )
        )
        # Issue: Schema that expect a nested result won't be able to
        # handle our flat graph structure. How to determine how much
        # to reassemble the node?

    return task_result(True, "Extension {} validated on node {}".format(
        extension_type, node.get('id')
    ))


def validate_extension_node(state, task_meta):
    try:
        if task_meta.get('node_id'):
            node_id = task_meta['node_id']
            node = get_node_by_id(state, node_id)
        else:
            node = get_node_by_path(state, task_meta['node_path'])
            node_id = node['id']
        node_type = list_of(node['type'])
        node_json = task_meta.get('node_json')  # Ok to be None
    except (KeyError, ValueError, IndexError, TypeError):
        raise TaskPrerequisitesError()

    try:
        types_to_test = [task_meta['type_to_test']]
    except KeyError:
        types_to_test = []
        for t in ALL_KNOWN_EXTENSIONS.keys():
            if t in node_type:
                types_to_test.append(t)

    if not types_to_test:
        return task_result(False, "Could not determine extension type to test")
    elif len(types_to_test) > 1:
        # If there is more than one extension, return each validation as a separate task
        actions = [
            add_task(VALIDATE_EXTENSION_NODE, node_id=node_id,
                     node_json=node_json, type_to_test=t)
            for t in types_to_test
        ]
        return task_result(
            True, "Multiple extension types {} discovered in node {}".format(
                abbreviate_value(types_to_test), node_id
            ), actions)
    else:
        return _validate_single_extension(node, types_to_test[0], node_json=node_json)
