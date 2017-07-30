class ttyP:
    def __init__(self, optionNum, textInput):
        endc = '\033[0m'  # Clear color and other terminal states
        clrLine = '\033[2K'  # Erases the entire current line.
        returnCur = "\r"

        def none():
            print(textInput)

        def header():
            print('\033[95m' + textInput + endc)

        def bold():
            print('\033[1m' + textInput + endc)

        def okblue():
            print('\033[94m' + textInput + endc)

        def okgreen():
            print('\033[92m' + textInput + endc)

        def underline():
            print('\033[4m' + textInput + endc)

        def warning():
            print('\033[93m' + textInput + endc)

        def fail():
            print('\033[91m' + textInput + endc)

        def grey():
            print('\033[2m' + textInput + endc)

        def lineStatus():
            print(clrLine + textInput + endc + returnCur, end='')

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
