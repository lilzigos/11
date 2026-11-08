"""Small allowlist for human-reviewed emulator input; never executes shell text."""
import re


def validate(document, run_id, next_sequence, width=1280, height=720):
    assert set(document) == {'run_id', 'sequence', 'actions'}, 'Unknown control fields'
    assert document['run_id'] == run_id, 'Control belongs to another workflow run'
    assert type(document['sequence']) is int and document['sequence'] == next_sequence, 'Unexpected sequence'
    actions = document['actions']
    assert isinstance(actions, list) and 1 <= len(actions) <= 20, 'Invalid action count'
    result = []

    def number(item, field, lower, upper):
        v = item[field]
        assert type(v) is int and lower <= v <= upper, 'Invalid ' + field
        return str(v)

    for a in actions:
        assert isinstance(a, dict), 'Action must be an object'
        op = a.get('op')
        if op == 'tap':
            assert set(a) == {'op', 'x', 'y'}
            result.append(('input', 'tap', number(a, 'x', 0, width - 1), number(a, 'y', 0, height - 1)))
        elif op == 'swipe':
            assert set(a) == {'op', 'x1', 'y1', 'x2', 'y2', 'ms'}
            result.append(('input', 'swipe', number(a, 'x1', 0, width - 1),
                           number(a, 'y1', 0, height - 1), number(a, 'x2', 0, width - 1),
                           number(a, 'y2', 0, height - 1), number(a, 'ms', 100, 3000)))
        elif op == 'text':
            assert set(a) == {'op', 'value'}
            assert isinstance(a['value'], str) and re.fullmatch(r'[A-Za-z0-9_]{1,24}', a['value'])
            result.append(('input', 'text', a['value']))
        elif op == 'key':
            assert set(a) == {'op', 'code'}
            assert type(a['code']) is int and a['code'] in (4, 61, 66, 67, 111)
            result.append(('input', 'keyevent', str(a['code'])))
        elif op == 'wait':
            assert set(a) == {'op', 'seconds'}
            result.append(('wait', number(a, 'seconds', 0, 15)))
        else:
            assert op in ('capture', 'restart', 'finish') and set(a) == {'op'}, 'Unsupported operation'
            result.append((op,))
    return result
