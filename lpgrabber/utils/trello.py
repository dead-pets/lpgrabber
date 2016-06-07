def get_trello_board(client, name, create=False):
    try:
        board = [b for b in client.list_boards() if b.name == name][0]
    except IndexError:
        if create:
            board = client.add_board(name)
            for trello_list in board.open_lists():
                trello_list.close()
        else:
            raise
    return board
