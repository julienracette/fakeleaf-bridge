from .OverleafClient import OverleafClient

def main() -> None:
    client = OverleafClient(debug=False)
    client.choose_project()
    client.connect_project()
    print(f"{client.selected_id} connected!")

if __name__ == "__main__":
    main()

