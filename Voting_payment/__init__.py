from otree.api import *
import re
import random
import json

doc = """
reflect the payment in the end
"""


class C(BaseConstants):
    NAME_IN_URL = 'Voting_payment'
    PLAYERS_PER_GROUP = 3
    NUM_ROUNDS = 1



class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    round_to_pay_block_one = models.StringField()
    money_to_pay_block_one = models.IntegerField()
    round_to_pay_block_two = models.IntegerField()
    money_to_pay_block_two = models.IntegerField()
    round_to_pay_block_three = models.IntegerField()
    money_to_pay_block_three = models.IntegerField()
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
    form_fields = ['Gender', 'How_choose_state', 'How_choose_info']
    @staticmethod

    def before_next_page(player: Player, timeout_happened):
        part = player.participant

        # ---------- block 1 ----------
        pay1, rnds1 = part.vars['Voting_block_one']  # rnds1 是 list
        player.money_to_pay_block_one = pay1
        player.round_to_pay_block_one = json.dumps(rnds1)   # 存成字符串，如 "[1, 3]"

        # ---------- block 2 ----------
        pay2, rnd2 = part.vars['Voting_block_two']  # rnd2 是单个 int
        player.money_to_pay_block_two = pay2
        player.round_to_pay_block_two = rnd2

        # ---------- block 3 ----------
        pay3, rnd3 = part.vars['Voting_block_three']
        player.money_to_pay_block_three = pay3
        player.round_to_pay_block_three = rnd3

        # ---------- 总额 + 到场费 ----------
        player.total_to_pay = pay1 + pay2 + pay3 + 5

        # 一次性写入 participant.payoff（别再 += 免得多加）
        part.payoff = player.total_to_pay


class Email(Page):
    form_model = 'player'
    form_fields = ['Email_address']

class ResultsWaitPage(WaitPage):
    wait_for_all_groups = True

class Payment(Page):
    pass


page_sequence = [Instruction, Survey, Email, ResultsWaitPage, Payment]