from otree.api import *
import random
import json


doc = """
Voting_real_treatment_irr_info
"""


class C(BaseConstants):
    NAME_IN_URL = 'Voting_real_treatment_irr_info'
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
    MAJORITY_O_4 = ['send to a player who got O', 'send to a player who got P', 'do not send to anyone']
    MAJORITY_P_4 = ['send to a player who got P', 'send to a player who got O', 'do not send to anyone']
    MAJORITY_O_3 = ['send to a player who got O', 'send to a player who got P', 'do not send to anyone']
    MAJORITY_P_3 = ['send to a player who got P', 'send to a player who got O', 'do not send to anyone']
    MINORITY_O_1 = ['send to a player who got P', 'do not send to anyone']
    MINORITY_P_1 = ['send to a player who got O', 'do not send to anyone']
    MINORITY_O_2 = ['send to a player who got O', 'send to a player who got P', 'do not send to anyone']
    MINORITY_P_2 = ['send to a player who got P', 'send to a player who got O', 'do not send to anyone']
    ALL_P = ['send to a player who got P', 'do not send to anyone']
    ALL_O = ['send to a player who got O', 'do not send to anyone']


class Subsession(BaseSubsession):
    def creating_session(self):
        self.group_randomly()


class Group(BaseGroup):
    state = models.StringField()
    p_count = models.IntegerField(initial=0)
    o_count = models.IntegerField(initial=0)
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
        p_count = 0
        o_count = 0
        for p in self.get_players():
            if p.irrinfo == 'p':
                p_count += 1
            elif p.irrinfo == 'o':
                o_count += 1
        self.p_count = p_count
        self.o_count = o_count


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
    irrinfo = models.CharField()
    selected_round = models.IntegerField()
    p_count = models.IntegerField()
    o_count = models.IntegerField()

    def get_decision_options(self):
        if self.p_count == 0:
            options = list(C.ALL_O)
        elif self.p_count == 1:
            if self.irrinfo == 'o':
                options = list(C.MAJORITY_O_4)
            else:
                options = list(C.MINORITY_P_1)
        elif self.p_count == 2:
            if self.irrinfo == 'o':
                options = list(C.MAJORITY_O_3)
            else:
                options = list(C.MINORITY_P_2)
        elif self.p_count == 3:
            if self.irrinfo == 'o':
                options = list(C.MINORITY_O_2)
            else:
                options = list(C.MAJORITY_P_3)
        elif self.p_count == 4:
            if self.irrinfo == 'o':
                options = list(C.MINORITY_O_1)
            else:
                options = list(C.MAJORITY_P_4)
        else:
            options = list(C.ALL_P)

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

                player.irrinfo = 'p' if random.random() < 1 / 2 else 'o'

            group.calculate_signals()
            for player in group.get_players():
                player.p_count = group.p_count
                player.o_count = group.o_count



class ResultsWaitPage1(WaitPage):
    wait_for_all_groups = True


class Info_and_decision(Page):
    form_model = 'player'
    form_fields = ['timeSpent1','decision']
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

        if player.irrinfo == 'p':
            player_irr_info = "purple"
        else:  # 'o'
            player_irr_info = "orange"

        player_signal_style = f"height: 1.2em; width: 1.2em; background-color: {player_signal_color}; border-radius: 50%; display: inline-block; vertical-align: middle; margin: 0 5px;"
        player_irrelevant_info = f"width: 0; height: 0; border-left: 0.6em solid transparent; border-right: 0.6em solid transparent; border-bottom: 1.2em solid {player_irr_info}; display: inline-block; vertical-align: middle; margin: 0 5px;"

        other_signals_info = []
        for p in player.group.get_players():
            if p.id_in_group != player.id_in_group:
                if p.signals == 'r':
                    signal_color = "red"
                else:  # 'b'
                    signal_color = "blue"

                if p.irrinfo == 'p':
                    irr_info = "purple"
                else:  # 'o'
                    irr_info = "orange"

                other_signals_info.append({
                    'player_id': p.id_in_group,
                    'signal_style': f"height: 1.2em; width: 1.2em; background-color: {signal_color}; border-radius: 50%; display: inline-block; vertical-align: middle; margin: 0 5px;",
                    'irrinfo': f"width: 0; height: 0; border-left: 0.6em solid transparent; border-right: 0.6em solid transparent; border-bottom: 1.2em solid {irr_info}; display: inline-block; vertical-align: middle; margin: 0 5px;"
                })

        return dict(
            quality=quality_display,
            player_signal_style=player_signal_style,
            player_irrelevant_info=player_irrelevant_info,
            other_signals_info=other_signals_info,
        )



class ResultsWaitPage2(WaitPage):
    wait_for_all_groups = True

    def after_all_players_arrive(self):
        groups = self.subsession.get_groups()

        for group in groups:
            group_players = group.get_players()

            for player in group_players:
                player.info_from_whom = str(player.id_in_group)

            for participant in group_players:
                if participant.decision == 'send to a player who got O':
                    eligible_players = [p for p in group_players if p.irrinfo == 'o' and p.id_in_group != participant.id_in_group]
                    if eligible_players:
                        chosen_receiver = random.choice(eligible_players)
                        chosen_receiver.info_from_whom += f",{participant.id_in_group}"
                        participant.chosen_receiver = chosen_receiver.id_in_group
                elif participant.decision == 'send to a player who got P':
                    eligible_players = [p for p in group_players if p.irrinfo == 'p' and p.id_in_group != participant.id_in_group]
                    if eligible_players:
                        chosen_receiver = random.choice(eligible_players)
                        chosen_receiver.info_from_whom += f",{participant.id_in_group}"
                        participant.chosen_receiver = chosen_receiver.id_in_group


class network_and_voting(Page):
    form_model = 'player'
    form_fields = ['timeSpent2','vote']

    @staticmethod
    def vars_for_template(player):
        all_players = player.group.get_players()
        participants_info = []

        info_sources = set(map(int, player.info_from_whom.split(',')))

        for participant in all_players:
            if participant.signals == 'r':
                player_signal_color = "red"
            else:  # b
                player_signal_color = "blue"

            if participant.irrinfo == 'p':
                player_irr_info = "purple"
            else:  # 'o'
                player_irr_info = "orange"

            player_signal_style = f"height: 1.2em; width: 1.2em; background-color: {player_signal_color}; border-radius: 50%; display: inline-block; vertical-align: middle; margin: 0 5px;"
            player_irrelevant_info = f"width: 0; height: 0; border-left: 0.6em solid transparent; border-right: 0.6em solid transparent; border-bottom: 1.2em solid {player_irr_info}; display: inline-block; vertical-align: middle; margin: 0 5px;"

            all_info = participant.info_from_whom

            if participant.qualities == 'l':
                quality_representation = "Box B"
            else:
                quality_representation = "Box A"

            box_info = quality_representation if participant.id_in_group in info_sources else 'Unknown'
            ball_info = player_signal_style if participant.id_in_group in info_sources else 'Unknown'

            participants_info.append({
                'id_in_group': participant.id_in_group,
                'quality_representation': quality_representation,
                'ball_info': ball_info,
                'player_irrelevant_info': player_irrelevant_info,
                'is_self': participant.id_in_group == player.id_in_group,
                'box_info': box_info,
                'all_info': all_info
            })

        participants_info = sorted(participants_info, key=lambda x: not x['is_self'])

        return {
            'participants_info': participants_info
        }


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


page_sequence = [StartRoundWaitPage, ResultsWaitPage1, Info_and_decision, ResultsWaitPage2, network_and_voting, ResultsWaitPage3, ResultsWaitPage4, ResultsWaitPage5]
