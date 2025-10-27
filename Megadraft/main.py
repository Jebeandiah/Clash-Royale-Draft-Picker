from boardGenerator import *

def main():
    # newBoard = Board()
    pass


def run_tests():
    newBoard = Board()
    print("Board Generated: ")
    print(newBoard)

    # Tests no repeats on board
    for i in range(10):
        newBoard.reset()
        assert(len(newBoard.board) == 36)

if __name__ == "__main__":
    print("Running Main!")
    main()
    print("Running Tests!")
    run_tests()
