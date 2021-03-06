from ..actions.action_types import ADD_TASK, RESOLVE_TASK, UPDATE_TASK
from ..tasks.task_types import VALIDATE_EXPECTED_NODE_CLASS, VALIDATE_PROPERTY, VALIDATE_RDF_TYPE_PROPERTY
from ..state import filter_active_tasks


def _task_to_add_exists(state, action):
    try:
        if action.get('name') == VALIDATE_EXPECTED_NODE_CLASS:
            task = [t for t in state if
                    action['name'] == t.get('name') and
                    action.get('node_id') == t.get('node_id')][0]

        elif action.get('name') in [VALIDATE_PROPERTY, VALIDATE_RDF_TYPE_PROPERTY]:
            task = [t for t in state if
                    action.get('node_id') == t.get('node_id') and
                    action.get('prop_name') == t.get('prop_name')][0]

        else:
            return False
    except IndexError:
        return False

    return True


def task_reducer(state=None, action=None):
    if state is None or len(state) == 0:
        state = []
        task_counter = 1
    else:
        task_counter = state[-1]['task_id'] + 1

    if action.get('type') == ADD_TASK and not _task_to_add_exists(state, action):
        new_task = {'task_id': task_counter, 'complete': False}
        for key in [k for k in action.keys() if k != 'type']:
            new_task[key] = action[key]
        return list(state) + [new_task]

    elif action.get('type') == RESOLVE_TASK:
        try:
            task = [t for t in state if t['task_id'] == action['task_id']][0]
        except KeyError:
            return state
        else:
            update = task.copy()
            update.update({
                'complete': True,
                'success': action.get('success'),
                'result': action.get('result')
            })
            return _new_state_with_updated_item(state, action['task_id'], update)

    elif action.get('type') == UPDATE_TASK:
        try:
            task = [t for t in state if t['task_id'] == action['task_id']][0]
        except KeyError:
            return state
        else:
            update = task.copy()
            for key in [k for k in action.keys() if k not in ('type', 'task_id',)]:
                update[key] = action[key]
            return _new_state_with_updated_item(state, action['task_id'], update)


    return state


def _new_state_with_updated_item(state, item_id, update):
    new_state = []
    for i in range(0, len(state)):
        if item_id != state[i].get('task_id'):
            new_state.append(state[i])
        else:
            new_state.append(update)
    return new_state
