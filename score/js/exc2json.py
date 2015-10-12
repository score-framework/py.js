import traceback
import textwrap


def exc2json(excinfo, untrace=[]):
    """
    Converts exception info (as returned by :func:`sys.exc_info`) into a
    3-tuple that can be converted into a json string by python's :mod:`json`
    library. It will consist of the exception name, the message and the stack
    trace as provided by :func:`traceback.extract_tb`::

        {
            type: 'ZeroDivisionError',
            message: 'division by zero',
            trace: [
                [<filename>, <lineno>, <line>],
                ...
            ]
        }

    It is possible to omit the last value of *excinfo*, effectively passing
    The optional parameter *untrace* contains file names that will be removed
    from the beginning of the stack trace.
    """
    trace = None
    if len(excinfo) > 2:
        trace = traceback.extract_tb(excinfo[2])
        untrace.append(__file__)
        while trace and any(skip for skip in untrace if skip in trace[0][0]):
            trace = trace[1:]
    return {
        'type': excinfo[0].__name__,
        'message': str(excinfo[1]),
        'trace': trace,
    }


def gen_excformat_js():
    """
    Generates a javascript function that can convert the return value of of a
    exc2json call to a human-readable stack trace. The resulting string will
    look a lot like the original python stack trace.
    """
    return textwrap.dedent('''
        define('lib/score/js/excformat', function() {
            return function excformat(exc) {
                if (typeof exc.trace === 'undefined') {
                    return exc.type + ': ' + exc.message
                }
                var msg = 'Traceback (most recent call last):\\n';
                for (var j = 0; j < exc.trace.length; j++) {
                    var frame = exc.trace[j];
                    msg += '  File "' + frame[0] +
                        '", line "' + frame[1] +
                        '", in ' + frame[2] + '\\n';
                    msg += '    ' + frame[3] + '\\n';
                }
                msg += '\\n' + exc.type + ': ' + exc.message;
                return msg;
            }
        });
    ''').strip()
