from otree.api import *
import random
import json


doc = """
Voting_real_treatment_no_links
"""


class C(BaseConstants):
    NAME_IN_URL = 'Voting_real_treatment_no_links'
    PLAYERS_PER_GROUP = 5
    NUM_ROUNDS = 15
    AMOUNT_SHARED_IF_WIN = 15
    AMOUNT_SHARED_IF_LOSE = 2
    CHOICES = [
        ('R', 'RED Box'),
        ('B', 'BLUE Box')
    ]
    STATES = ['R', 'B']
    QUALITIES = ['h', 'l']
    MAJORITY_B_4 = ['send to a player who got B', 'send to a player who got R', 'do not send to anyone']
    MAJORITY_R_4 = ['send to a player who got R', 'send to a player who got B', 'do not send to anyone']
    MAJORITY_B_3 = ['send to a player who got B', 'send to a player who got R', 'do not send to anyone']
    MAJORITY_R_3 = ['send to a player who got R', 'send to a player who got B', 'do not send to anyone']
    MINORITY_B_1 = ['send to a player who got R', 'do not send to anyone']
    MINORITY_R_1 = ['send to a player who got B', 'do not send to anyone']
    MINORITY_B_2 = ['send to a player who got B', 'send to a player who got R', 'do not send to anyone']
    MINORITY_R_2 = ['send to a player who got R', 'send to a player who got B', 'do not send to anyone']
    ALL_R = ['send to a player who got R', 'do not send to anyone']
    ALL_B = ['send to a player who got B', 'do not send to anyone']


class Subsession(BaseSubsession):
    def creating_session(self):
        self.group_randomly()


class Group(BaseGroup):
    state = models.StringField()
    r_count = models.IntegerField(initial=0)
    b_count = models.IntegerField(initial=0)
    chosen_player_id = models.IntegerField()
    chosen_player_vote = models.StringField()
    def set_payoffs(self):
        chosen_player = random.choice(self.get_players())
        self.chosen_player_id = chosen_player.id_in_group
        self.chosen_player_vote = chosen_player.vote
        if chosen_player.vote == self.state:
            payoff = C.AMOUNT_SHARED_IF_WIN
        else:
            payoff = C.AMOUNT_SHARED_IF_LOSE
        for p in self.get_players():
            p.payoff = payoff

    def calculate_signals(self):
        r_count = 0
        b_count = 0
        for p in self.get_players():
            if p.signals == 'r':
                r_count += 1
            elif p.signals == 'b':
                b_count += 1
        self.r_count = r_count
        self.b_count = b_count


class Player(BasePlayer):
    timeSpent1 = models.FloatField()
    timeSpent2 = models.FloatField()
    decision = models.StringField()
    info_from_whom = models.StringField()
    chosen_receiver = models.IntegerField(null=True)
    vote = models.StringField(widget=widgets.RadioSelect, choices=C.CHOICES)
    state = models.StringField()
    qualities = models.StringField()
    signals = models.CharField()
    selected_round = models.IntegerField()
    r_count = models.IntegerField()
    b_count = models.IntegerField()

    def get_decision_options(self):
        if self.r_count == 0:
            options = list(C.ALL_B)
        elif self.r_count == 1:
            if self.signals == 'b':
                options = list(C.MAJORITY_B_4)
            else:  # signals == 'r'
                options = list(C.MINORITY_R_1)
        elif self.r_count == 2:
            if self.signals == 'b':
                options = list(C.MAJORITY_B_3)
            else:  # signals == 'r'
                options = list(C.MINORITY_R_2)
        elif self.r_count == 3:
            if self.signals == 'b':
                options = list(C.MINORITY_B_2)
            else:  # signals == 'r'
                options = list(C.MAJORITY_R_3)
        elif self.r_count == 4:
            if self.signals == 'b':
                options = list(C.MINORITY_B_1)
            else:  # signals == 'r'
                options = list(C.MAJORITY_R_4)
        else:  # r_count = 5
            options = list(C.ALL_R)

        random.shuffle(options)
        return options

class StartRoundWaitPage(WaitPage):
    wait_for_all_groups = True
    @staticmethod
    def after_all_players_arrive(subsession):
        subsession.group_randomly()
        for group in subsession.get_groups():
            chosen_state = random.choice(C.STATES)
            group.state = chosen_state
            for player in group.get_players():
                player.state = chosen_state
                qualities = random.choice(C.QUALITIES)
                player.qualities = qualities

                if player.state == 'R':
                    if player.qualities == 'h':
                        player.signals = 'r' if random.random() < 7 / 8 else 'b'
                    else:  # 'l'
                        player.signals = 'r' if random.random() < 4 / 7 else 'b'
                else:  # 'B'
                    if player.qualities == 'h':
                        player.signals = 'r' if random.random() < 1 / 7 else 'b'
                    else:  # 'l'
                        player.signals = 'r' if random.random() < 3 / 7 else 'b'

            group.calculate_signals()
            for player in group.get_players():
                player.r_count = group.r_count
                player.b_count = group.b_count



class ResultsWaitPage1(WaitPage):
    wait_for_all_groups = True


class Info_and_decision(Page):
    form_model = 'player'
    form_fields = ['timeSpent1']
    @staticmethod
    def vars_for_template(player):
        if player.qualities == 'l':
            quality_display = "Box B"
        else:
            quality_display = "Box A"

        if player.signals == 'r':
            player_signal_color = "red"
        else:  # 'b'
            player_signal_color = "blue"

        player_signal_style = f"height: 1.2em; width: 1.2em; background-color: {player_signal_color}; border-radius: 50%; display: inline-block; vertical-align: middle; margin: 0 5px;"

        other_signals_info = []
        for p in player.group.get_players():
            if p.id_in_group != player.id_in_group:
                if p.signals == 'r':
                    signal_color = "red"
                else:  # 'b'
                    signal_color = "blue"

                other_signals_info.append({
                    'player_id': p.id_in_group,
                    'signal_style': f"height: 1.2em; width: 1.2em; background-color: {signal_color}; border-radius: 50%; display: inline-block; vertical-align: middle; margin: 0 5px;",
                })

        return dict(
            quality=quality_display,
            player_signal_style=player_signal_style,
            other_signals_info=other_signals_info,
        )


class network_and_voting(Page):
    form_model = 'player'
    form_fields = ['timeSpent2','vote']

    @staticmethod
    def vars_for_template(player):
        if player.qualities == 'l':
            quality_display = "Box B"
        else:
            quality_display = "Box A"

        if player.signals == 'r':
            player_signal_color = "red"
        else:  # 'b'
            player_signal_color = "blue"

        player_signal_style = f"height: 1.2em; width: 1.2em; background-color: {player_signal_color}; border-radius: 50%; display: inline-block; vertical-align: middle; margin: 0 5px;"

        other_signals_info = []
        for p in player.group.get_players():
            if p.id_in_group != player.id_in_group:
                if p.signals == 'r':
                    signal_color = "red"
                else:  # 'b'
                    signal_color = "blue"

                other_signals_info.append({
                    'player_id': p.id_in_group,
                    'signal_style': f"height: 1.2em; width: 1.2em; background-color: {signal_color}; border-radius: 50%; display: inline-block; vertical-align: middle; margin: 0 5px;",
                })

        return dict(
            quality=quality_display,
            player_signal_style=player_signal_style,
            other_signals_info=other_signals_info,
        )


class ResultsWaitPage3(WaitPage):

    def after_all_players_arrive(self):
        self.group.set_payoffs()


class ResultsWaitPage4(WaitPage):
    wait_for_all_groups = True


class ResultsWaitPage5(WaitPage):
    def is_displayed(player:Player):
        return player.round_number==C.NUM_ROUNDS

    def after_all_players_arrive(self):
        selected_round = random.randint(1, C.NUM_ROUNDS)
        for player in self.group.get_players():
            player_in_selected_round = player.in_round(selected_round)
            player.selected_round = selected_round
            player.payoff = player_in_selected_round.payoff

            player.participant.vars[__name__] = [int(player.payoff), int(selected_round)]


page_sequence = [StartRoundWaitPage, ResultsWaitPage1, Info_and_decision, network_and_voting, ResultsWaitPage3, ResultsWaitPage4, ResultsWaitPage5]
