num=0
i=1
while i==1:
    print("\nPlayer 1's turn: ")
    p1Choice=int(input("How many digits to go from " + str(num) + "? "))
    if p1Choice==1:
        print(str(num+1))
        num=num+1
    elif p1Choice==2:
        print(str(num+1) + "," + str(num+2))
        num=num+2
    elif p1Choice==3:
        print(str(num+1) + "," + str(num+2) + "," + str(num+3))
        num=num+3
    else:
        print("Invalid choice")
    lastChoice="p1"

    if num>=15:
        break

    print("\nPlayer 2's turn: ")
    p2Choice=int(input("How many digits to go from " + str(num) + "? "))
    if p2Choice==1:
        print(str(num+1))
        num=num+1
    elif p2Choice==2:
        print(str(num+1) + "," + str(num+2))
        num=num+2
    elif p2Choice==3:
        print(str(num+1) + "," + str(num+2) + "," + str(num+3))
        num=num+3
    else:
        print("Invalid choice")
    lastChoice="p2"

    if num>=15:
        break

if lastChoice=="p1":
    print("\nPlayer 2 wins!")
else:
    print("\nPlayer 1 wins!")
