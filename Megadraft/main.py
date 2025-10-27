from boardGenerator import *

def main():
    newBoard = Board()


def run_tests():
    newBoard = Board()
    print("Testing Board Generator")
    print(newBoard)
    print(len(newBoard.cards),"\n")

    print("Testing No Repeats")
    for i in range(10):
        newBoard.reset()
        print(len(set(newBoard.board)))

if __name__ == "__main__":
    print("Running Main!")
    main()
    print("Running Tests!")
    run_tests()
