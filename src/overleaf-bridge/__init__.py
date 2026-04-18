from OverleafClient import OverleafClient
import sys
tty_path= sys.argv[1]
with open(tty_path, "w") as tty:
    print("\033[H\033[2J", end="",file=tty)

if __name__ =="__main__":
    client =  OverleafClient(debug=False)
    client.choose_project()
    #client.fetch_doc()
    client.connect_project()
    print(f"{client.selected_id} fetched !")

