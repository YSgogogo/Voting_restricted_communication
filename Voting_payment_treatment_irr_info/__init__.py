from otree.api import *
import re
import random

doc = """
reflect the payment in the end
"""


class C(BaseConstants):
    NAME_IN_URL = 'Voting_payment_treatment_irr_info'
    PLAYERS_PER_GROUP = 5
    NUM_ROUNDS = 1



class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    round_to_pay = models.IntegerField()
    money_to_pay = models.IntegerField()
    total_to_pay = models.IntegerField()

    Gender =  models.IntegerField(
        widget=widgets.RadioSelect,
        choices=[
            [0, 'Male'],
            [1, 'Female'],
            [2, 'Prefer not to say'],
        ]
    )
    How_choose_info = models.StringField()
    How_choose_state = models.StringField()
    Email_address = models.StringField()


class Instruction(Page):
    pass



class Survey(Page):
    form_model = 'player'
    form_fields = ['Gender', 'How_choose_info', 'How_choose_state']
    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        participant = player.participant
        player.money_to_pay = int(participant.vars['Voting_real_treatment_irr_info'][0])
        player.round_to_pay = int(participant.vars['Voting_real_treatment_irr_info'][1])
        player.total_to_pay = int(participant.vars['Voting_real_treatment_irr_info'][0])+5
        participant.payoff = 0

        participant.payoff += player.money_to_pay

class Email(Page):
    form_model = 'player'
    form_fields = ['Email_address']

class ResultsWaitPage(WaitPage):
    wait_for_all_groups = True

class Payment(Page):
    pass


page_sequence = [Instruction, Survey, Email, ResultsWaitPage, Payment]