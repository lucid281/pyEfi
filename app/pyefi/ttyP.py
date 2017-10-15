class ttyP:
    def __init__(self, optionNum, textInput):
        endc = '\033[0m'  # Clear color and other terminal states
        clrLine = '\033[2K'  # Erases the entire current line.
        returnCur = '\r'

        def none():
            print(textInput)

        def header():
            print(f'\033[95m{textInput}{endc}')

        def bold():
            print(f'\033[1m{textInput}{endc}')

        def okblue():
            print(f'\033[94m{textInput}{endc}')

        def okgreen():
            print(f'\033[92m{textInput}{endc}')

        def underline():
            print(f'\033[4m{textInput}{endc}')

        def warning():
            print(f'\033[93m{textInput}{endc}')

        def fail():
            print(f'\033[91m{textInput}{endc}')

        def grey():
            print(f'\033[2m{textInput}{endc}')

        def lineStatus():
            print(f'{clrLine}{textInput}{endc}{returnCur}', end='')

        options = {0: none,
                   1: header,
                   2: bold,
                   3: okblue,
                   4: okgreen,
                   5: underline,
                   6: warning,
                   7: fail,
                   8: grey,
                   9: lineStatus
                   }

        options[optionNum]()
        return
