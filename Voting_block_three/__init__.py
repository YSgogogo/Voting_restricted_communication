from otree.api import *
import random


doc = """Three-player voting experiment with full, public information and no messaging choices**."""

# ------------------------------------------------------------------
#  Constants
# ------------------------------------------------------------------
class C(BaseConstants):
    NAME_IN_URL       = 'Voting_block_three'
    PLAYERS_PER_GROUP = 3
    NUM_ROUNDS        = 10
    AMOUNT_CORRECT    = 2
    CHOICES           = [('R', 'RED Box'), ('B', 'BLUE Box')]
    STATES            = ['R', 'B']
    QUALITIES         = ['h', 'l']   # 30 % high / 70 % low


# ------------------------------------------------------------------
#  Subsession
# ------------------------------------------------------------------
class Subsession(BaseSubsession):
    def creating_session(self):
        self.group_randomly()


# ------------------------------------------------------------------
#  Group
# ------------------------------------------------------------------
class Group(BaseGroup):
    state   = models.StringField()
    r_count = models.IntegerField()
    b_count = models.IntegerField()

    # ---------- 信号生成 ----------
    def _draw_signals_once(self):
        self.state = random.choice(C.STATES)
        for p in self.get_players():
            p.qualities = 'h' if random.random() < 0.30 else 'l'
            p.state     = self.state

            if self.state == 'R':
                p.signals = (
                    'r' if (p.qualities == 'h' and random.random() < 8/9)
                    or   (p.qualities == 'l' and random.random() < 5/9)
                    else 'b'
                )
            else:  # state == 'B'
                p.signals = (
                    'r' if (p.qualities == 'h' and random.random() < 1/9)
                    or   (p.qualities == 'l' and random.random() < 4/9)
                    else 'b'
                )
        self._count_signals()

    def _count_signals(self):
        self.r_count = sum(1 for p in self.get_players() if p.signals == 'r')
        self.b_count = C.PLAYERS_PER_GROUP - self.r_count

    def generate_valid_signals(self):
        """Draw signals until not unanimous; then make *all* information immediately public."""
        while True:
            self._draw_signals_once()
            if self.r_count not in (0, C.PLAYERS_PER_GROUP):
                break
        # Store counts and *full* info for every participant
        id_list_all = ','.join(str(p.id_in_group) for p in self.get_players())
        for p in self.get_players():
            p.r_count, p.b_count = self.r_count, self.b_count
            p.info_from_whom     = id_list_all  # everyone
            # Build info_codes such as Rh, Bl, … in id order
            codes = []
            for src in self.get_players():
                sig = 'R' if src.signals == 'r' else 'B'
                codes.append(f'{sig}{src.qualities}')
            p.info_codes = ','.join(codes)

    # ---------- 收益 ----------
    def set_payoffs(self):
        correct_cnt   = sum(1 for p in self.get_players() if p.vote == self.state)
        payoff_record = correct_cnt * C.AMOUNT_CORRECT
        for p in self.get_players():
            p.payoff_record = payoff_record


# ------------------------------------------------------------------
#  Player
# ------------------------------------------------------------------
class Player(BasePlayer):
    # ---- 计时 ----
    timeSpent1 = models.FloatField()
    timeSpent2 = models.FloatField()

    # ---- 投票 ----
    vote = models.StringField(widget=widgets.RadioSelect, choices=C.CHOICES)

    # ---- 玩家信息 ----
    state     = models.StringField()
    signals   = models.CharField()
    qualities = models.StringField()

    info_from_whom = models.StringField(initial='')
    info_codes     = models.StringField(initial='')

    # ---- 收益 ----
    payoff_record  = models.IntegerField(initial=0)
    selected_round = models.IntegerField()

    # ---- 统计 ----
    r_count = models.IntegerField()
    b_count = models.IntegerField()


# ------------------------------------------------------------------
#  Pages
# ------------------------------------------------------------------
class StartRoundWaitPage(WaitPage):
    wait_for_all_groups = True

    @staticmethod
    def after_all_players_arrive(subsession):
        subsession.group_randomly()
        for g in subsession.get_groups():
            g.generate_valid_signals()


class Main_Instructions(Page):
    @staticmethod
    def is_displayed(p):
        return p.round_number == 1


class ResultsWaitPage1(WaitPage):
    wait_for_all_groups = True


class Info_and_decision(Page):
    """Now purely informational – no choices required."""
    form_model  = 'player'
    form_fields = ['timeSpent1']

    @staticmethod
    def vars_for_template(player):
        # ---------- 自己 ----------
        my_img   = 'IndividualDecision/red_urn.png'  if player.signals == 'r' else 'IndividualDecision/blue_urn.png'
        my_grade = 'S' if player.qualities == 'h' else 'W'

        # ---------- 另外两名组员（信息完全公开） ----------
        others = []
        for p in player.group.get_players():
            if p == player:
                continue
            img = 'IndividualDecision/red_urn.png' if p.signals == 'r' else 'IndividualDecision/blue_urn.png'
            grade = 'S' if p.qualities == 'h' else 'W'
            others.append(dict(
                id          = p.id_in_group,
                img_src     = img,
                grade_label = grade
            ))

        return dict(
            my_img     = my_img,
            my_grade   = my_grade,
            my_id      = player.id_in_group,
            other_urns = others,  # 两项
        )


# ---------------- 投票 ----------------
class network_and_voting(Page):
    form_model  = 'player'
    form_fields = ['timeSpent2', 'vote']

    @staticmethod
    def vars_for_template(player):
        rows = []
        for p in player.group.get_players():
            # 信号点颜色
            col = 'red' if p.signals == 'r' else 'blue'
            css = (f"height:1.2em;width:1.2em;background-color:{col};"
                   "border-radius:50%;display:inline-block;vertical-align:middle;margin:0 5px;")
            # 质量盒信息（全部公开）
            qual = "Box A" if p.qualities == 'h' else "Box B"
            rows.append(dict(
                id_in_group         = p.id_in_group,
                is_self             = (p == player),
                player_signal_style = css,
                box_info            = qual,
            ))
        # 自己排第一行
        rows.sort(key=lambda d: not d['is_self'])
        return dict(participants_info=rows)


# ---------------- 本轮收益 ----------------
class ResultsWaitPage3(WaitPage):
    def after_all_players_arrive(self):
        self.group.set_payoffs()


class ResultsWaitPage4(WaitPage):
    wait_for_all_groups = True


# ---------------- 随机抽轮 ----------------
class ResultsWaitPage5(WaitPage):
    def is_displayed(p):
        return p.round_number == C.NUM_ROUNDS

    def after_all_players_arrive(self):
        rnd = random.randint(1, C.NUM_ROUNDS)
        for p in self.group.get_players():
            p.selected_round = rnd
            p.payoff = p.in_round(rnd).payoff_record

            p.participant.vars[__name__] = [int(p.payoff), rnd]


class FinalResults(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS


# ------------------------------------------------------------------
page_sequence = [
    StartRoundWaitPage,
    Main_Instructions,
    ResultsWaitPage1,
    Info_and_decision,
    network_and_voting, ResultsWaitPage3,
    ResultsWaitPage4, ResultsWaitPage5, FinalResults
]
