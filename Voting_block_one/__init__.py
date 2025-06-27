from otree.api import *
import random


# ════════════════════════════════════════════════════════════════
#  17 rounds of individual decisions, including all cases
# ════════════════════════════════════════════════════════════════
class C(BaseConstants):
    NAME_IN_URL = 'individual_decision'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 17
    NUM_PAYING_ROUNDS = 5

    TASKS = [
        dict(prob=8/9, image_RRB='IndividualDecision/RhRB.png',
                       image_BBR='IndividualDecision/BhBR.png'),
        dict(prob=5/9, image_RRB='IndividualDecision/RlRB.png',
                       image_BBR='IndividualDecision/BlBR.png'),
        dict(prob=169/369, image_RRB='IndividualDecision/BhRR.png',
                       image_BBR='IndividualDecision/RhBB.png'),
        dict(prob=676/801, image_RRB='IndividualDecision/BlRR.png',
                       image_BBR='IndividualDecision/RlBB.png'),
        dict(prob=125/333, image_RRB='IndividualDecision/RlRlB.png',
                       image_BBR='IndividualDecision/BlBlR.png'),
        dict(prob=200/252, image_RRB='IndividualDecision/RlRhB.png',
                       image_BBR='IndividualDecision/BlBhR.png'),
        dict(prob=320/333, image_RRB='IndividualDecision/RhRhB.png',
                       image_BBR='IndividualDecision/BhBhR.png'),
        dict(prob=65/225, image_RRB='IndividualDecision/RlRBh.png',
                       image_BBR='IndividualDecision/BlBRh.png'),
        dict(prob=6.5/9, image_RRB='IndividualDecision/RlRBl.png',
                       image_BBR='IndividualDecision/BlBRl.png'),
        dict(prob=6.5/9, image_RRB='IndividualDecision/RhRBh.png',
                       image_BBR='IndividualDecision/BhBRh.png'),
        dict(prob=416/441, image_RRB='IndividualDecision/RhRBl.png',
                       image_BBR='IndividualDecision/BhBRl.png'),
        dict(prob=5/9, image_RRB='IndividualDecision/RlRlBl.png',
                       image_BBR='IndividualDecision/BlBlRl.png'),
        dict(prob=25/233, image_RRB='IndividualDecision/RlRlBh.png',
                       image_BBR='IndividualDecision/BlBlRh.png'),
        dict(prob=8/9, image_RRB='IndividualDecision/RlRhBl.png',
                       image_BBR='IndividualDecision/BlBhRl.png'),
        dict(prob=5/9, image_RRB='IndividualDecision/RlRhBh.png',
                       image_BBR='IndividualDecision/BlBhRh.png'),
        dict(prob=256/261, image_RRB='IndividualDecision/RhRhBl.png',
                       image_BBR='IndividualDecision/BhBhRl.png'),
        dict(prob=8/9, image_RRB='IndividualDecision/RhRhBh.png',
                       image_BBR='IndividualDecision/BhBhRh.png'),
    ]

    AMOUNT_CORRECT   = 1     # each correct decisions receive 1 payoff
    AMOUNT_INCORRECT = 0     # each wrong decisions receive 0 payoff



class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    choice = models.StringField(
        choices=[('R', 'RED'), ('B', 'BLUE')],
        widget=widgets.RadioSelect,
        label='Please guess the occurred state based on the information you have received above?'
    )


    task_number    = models.IntegerField()
    prob_base      = models.FloatField()
    Majority       = models.StringField()    # 'R' or 'B'
    image_file     = models.StringField()    # get graph

    win           = models.BooleanField()    # correct or not
    payoff_record = models.IntegerField()    # payoff


    selected_rounds = models.StringField()   # select rounds
    total_score     = models.IntegerField()


# ════════════════════════════════════════════════════════════════
#  2. get random rounds for payment and which graph to show (RRB or BBR)
# ════════════════════════════════════════════════════════════════
def creating_session(subsession: Subsession):

    if subsession.round_number != 1:
        return

    for player in subsession.get_players():

        # (a) random order
        order = list(range(C.NUM_ROUNDS))
        random.shuffle(order)

        for rnd, task_idx in enumerate(order, start=1):
            pl = player.in_round(rnd)
            pl.task_number = task_idx

            task = C.TASKS[task_idx]
            prob = task['prob']

            # random RRB or BBR
            if random.random() < 0.5:
                pl.Majority = 'R'
                pl.prob_base      = prob
                pl.image_file     = task['image_RRB']
            else:
                pl.Majority = 'B'
                pl.prob_base      = prob
                pl.image_file     = task['image_BBR']

        # (c) random 5 rounds
        selected = random.sample(range(1, C.NUM_ROUNDS + 1), C.NUM_PAYING_ROUNDS)
        player.in_round(C.NUM_ROUNDS).selected_rounds = ','.join(map(str, selected))


# ════════════════════════════════════════════════════════════════
#  3. decision for 17 rounds
# ════════════════════════════════════════════════════════════════
class Welcome(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1


class General_Instructions(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1


class Main_Instructions(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1


class DecisionPage(Page):
    form_model  = 'player'
    form_fields = ['choice']

    @staticmethod
    def vars_for_template(player: Player):

        return dict(
            image_file    = player.image_file,
        )

    @staticmethod
    def before_next_page(player: Player, timeout_happened):

        win_prob = player.prob_base if player.choice == player.Majority \
                   else 1 - player.prob_base
        player.win = random.random() < win_prob
        player.payoff_record = (
            C.AMOUNT_CORRECT if player.win else C.AMOUNT_INCORRECT
        )


# ════════════════════════════════════════════════════════════════
#  4. result page
# ════════════════════════════════════════════════════════════════
class FinalResults(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS


    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        rnds  = list(map(int, player.selected_rounds.split(',')))
        total = sum(player.in_round(r).payoff_record for r in rnds)
        player.total_score = total
        player.payoff      = total   # final payoff


        player.participant.vars[__name__] = [total, rnds]

# ════════════════════════════════════════════════════════════════
#  5. page sequence
# ════════════════════════════════════════════════════════════════
page_sequence = [
    Welcome,
    General_Instructions,
    Main_Instructions,
    DecisionPage,
    FinalResults,
]
