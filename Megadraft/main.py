#############################
#                           #
#     Main File for Bot     #
#                           #
#############################

"""
Check dependencies to make sure everything will
thats needed is installed and running properly.
"""
print("--------------------------------------------")
print("Checking Dependencies... ")
try:
    # maybe from boardGenerator import * is better
    from boardGenerator import Board
    from boardGenerator import cards
    from boardGenerator import all_cards
    print("\tImported Files Successfully!")
except:
    print("\tUnable to import files")

try:
    import torch
    print("\tImported PyTorch Successfully!")
    print("\t\tPyTorch version:", torch.__version__)
except:
    print("\tUnable to import: PyTorch")

if torch:
    try:
        assert(torch.cuda.is_available())
        print("\t\tCUDA Availability: ", torch.cuda.is_available())
        print("\t\tCUDA Version: ", torch.version.cuda)
    except:
        print("\t\tCUDA Availability: ", torch.cuda.is_available())
        print("\t\tUnable to use CUDA. This is okay")
      
print("--------------------------------------------")

def main():
    pass

if __name__ == "__main__":
    print("Running Main!")
    main()

