
def add_trello_auth_arguments(parser):
    parser.add_argument(
        '--trello-key', type=str, required=False,
        help="You can get one at https://trello.com/app-key"
    )
    parser.add_argument(
        '--trello-secret', type=str, required=False,
        help="You can get one at https://trello.com/app-key"
    )
    parser.add_argument(
        '--trello-token', type=str, required=False,
        help="You can get one at https://trello.com/1/connect?" +
             "key=YOUR_TRELLO_KEY&name=bugfix-app&response_type=token&" +
             "scope=read,write&expiration=never"
    )
    parser.add_argument(
        '--trello-token-secret', type=str, required=False,
    )
    return parser


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
