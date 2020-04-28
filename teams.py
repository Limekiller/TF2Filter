

def check_teams(kill_relationship):

    if kill_relationship[0] in teams_dict:
        if teams_dict[kill_relationship[0]] == 'red':
            team = 'red'
        else:
            team = 'blue'

        if kill_relationship[1] in users_dict:
            search_and_add_teams(kill_relationship[1], team)

    elif kill_relationship[1] in teams_dict:
        if teams_dict[kill_relationship[1]] == 'red':
            team = 'red'
        else:
            team = 'blue'

        if kill_relationship[0] in users_dict:
            search_and_add_teams(kill_relationship[0], team)


def search_and_add_teams(current_node, team, checked_nodes=[]):
    if current_node not in checked_nodes:
        checked_nodes.append(current_node)
        for user in users_dict[current_node][0]:
            search_and_add_teams(user, team, checked_nodes)

        if team == 'red':
            team = 'blue'
        else:
            team = 'red'

        for user in users_dict[current_node][1]:
            search_and_add_teams(user, team, checked_nodes)

        teams_dict[current_node] = team


def synchronize_teammates(current_node, opponent, checked_list):
    set_to_check = users_dict[current_node][0].copy()
    for i in set_to_check:
        if i not in checked_list:
            checked_list.append(i)
            synchronize_teammates(i, opponent, checked_list)
            users_dict[i][0].add(opponent)
    users_dict[current_node][0].add(opponent)


def synchronize_opponents(current_node, opponent, checked_list):
    set_to_check = users_dict[current_node][0].copy()
    for i in set_to_check:
        if i not in checked_list:
            checked_list.append(i)
            synchronize_opponents(i, opponent, checked_list)
            users_dict[i][1].add(opponent)
    users_dict[current_node][1].add(opponent)


def handle_player_interaction(hit_sentence):
    killer, victim = hit_sentence.split(' killed ')
    victim = victim.split(' with ')[0]
    print(killer, victim)

    if killer not in users_dict.keys():
        users_dict[killer] = [set(), {victim}]
    else:
        users_dict[killer][1].add(victim)
    if victim not in users_dict.keys():
        users_dict[victim] = [set(), {killer}]
    else:
        users_dict[victim][1].add(killer)

    print(users_dict)
    for player in users_dict.keys():
        for i in users_dict[player][1]:
            for j in users_dict[player][1]:
                synchronize_teammates(j, i, [])
        for i in users_dict[player][0]:
            set_to_check = users_dict[player][1].copy()
            for j in set_to_check:
                synchronize_opponents(j, i, [])

    check_teams([killer, victim])
    print(teams_dict)


teams_dict = {
    'Limekiller': 'red'
}
users_dict = {
}


