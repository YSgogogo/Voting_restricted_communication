from otree.api import *
import random
from itertools import permutations

doc = """
Three-player voting experiment with send/receive decisions.
"""

# ------------------------------------------------------------------
#  Constants
# ------------------------------------------------------------------
class C(BaseConstants):
    NAME_IN_URL       = 'A_Voting_two'
    PLAYERS_PER_GROUP = 3
    NUM_ROUNDS        = 10
    AMOUNT_CORRECT    = 2
    CHOICES           = [('R', 'RED Box'), ('B', 'BLUE Box')]
    STATES            = ['R', 'B']
    QUALITIES         = ['h', 'l']


# ------------------------------------------------------------------
#  build pre-generated signal table
# ------------------------------------------------------------------
def build_signal_table(M: int = 1000):
    """预先生成 M 条三人组记录，每条含真实 state、各玩家 (signal, quality)。"""
    table = []
    for _ in range(M):
        state = random.choice(C.STATES)
        group = {'state': state, 'players': {}}

        for pid in (1, 2, 3):
            qual = 'h' if random.random() < 0.30 else 'l'

            # 条件化信号概率
            if state == 'R':
                sig = 'r' if (qual == 'h' and random.random() < 8/9) or \
                             (qual == 'l' and random.random() < 5/9) else 'b'
            else:
                sig = 'r' if (qual == 'h' and random.random() < 1/9) or \
                             (qual == 'l' and random.random() < 4/9) else 'b'

            group['players'][pid] = {'qualities': qual, 'signals': sig}

        table.append(group)
    return table


# ------------------------------------------------------------------
#  Subsession
# ------------------------------------------------------------------
class Subsession(BaseSubsession):
    def creating_session(self):
        if self.round_number == 1:
            self.session.vars['signal_table'] = build_signal_table(1000)
            self.session.vars['used_records'] = set()


# ------------------------------------------------------------------
#  Group
# ------------------------------------------------------------------
class Group(BaseGroup):
    state   = models.StringField()
    r_count = models.IntegerField()
    b_count = models.IntegerField()

    # 组内 r / b 信号计数（用于显示）
    def _count_signals(self):
        self.r_count = sum(1 for p in self.get_players() if p.signals == 'r')
        self.b_count = C.PLAYERS_PER_GROUP - self.r_count

    def set_payoffs(self):
        correct = sum(1 for p in self.get_players() if p.vote == self.state)
        payoff = correct * C.AMOUNT_CORRECT
        for p in self.get_players():
            p.payoff_record = payoff
# ------------------------------------------------------------------
#  Player
# ------------------------------------------------------------------
class Player(BasePlayer):
    # —— 计时 ——————————————————————————
    timeSpent = models.FloatField()

    # —— 决策 ——————————————————————————
    vote            = models.StringField(widget=widgets.RadioSelect,
                                         choices=C.CHOICES)

    # —— 私有信息 ————————————————————
    state     = models.StringField()
    signals   = models.CharField()
    qualities = models.StringField()

    # —— 信息网络 & 记录 ———————————
    payoff_record   = models.IntegerField(initial=0)
    selected_round  = models.IntegerField()

    # 显示用
    r_count         = models.IntegerField()
    b_count         = models.IntegerField()
    current_pattern = models.StringField()

# ------------------------------------------------------------------
#  Pages

class StartRoundWaitPage(WaitPage):
    wait_for_all_groups = True

    def after_all_players_arrive(self):
        self.subsession.group_randomly()

        sv = self.session.vars
        if 'signal_table' not in sv:
            sv['signal_table'] = build_signal_table(1000)
            sv['used_records'] = set()

        table = sv['signal_table']
        used_idx = sv['used_records']

        rounds_req = {
            'solo': ['rh_rb', 'rl_rb', 'bh_br', 'bl_br', 'rh_bb', 'rl_bb', 'bh_rr', 'bl_rr'],
            'pair': [],
        }

        def pattern_match(slot_tag: str, pattern: str, others_signals: list) -> bool:
            if '_' in pattern:
                left, right = pattern.split('_')
                if slot_tag != left:
                    return False
                if right in ['br', 'rb']:
                    return 'b' in others_signals and 'r' in others_signals
                elif right == 'rr':
                    return others_signals.count('r') == 2
                elif right == 'bb':
                    return others_signals.count('b') == 2
                else:
                    return False
            else:
                return slot_tag == pattern

        def find_pattern_from_signals(tag, others_signals):
            for pattern in rounds_req['solo']:
                if pattern_match(tag, pattern, others_signals):
                    return pattern
            return 'NO_MATCH'

        for g in self.subsession.get_groups():
            needs = {}
            for p in g.get_players():
                seen = p.participant.vars.get('patterns_seen_two', [])
                solo_seen = [x for x in seen if '+' not in x]
                need_solo = [x for x in rounds_req['solo'] if x not in solo_seen]
                if not need_solo:
                    need_solo = rounds_req['solo']
                needs[p.id_in_subsession] = need_solo

            best_match = None
            for tier in [3, 2, 1, 0]:
                for idx, rec in enumerate(table):
                    if idx in used_idx:
                        continue
                    slots = [(sid, info['signals'] + info['qualities']) for sid, info in rec['players'].items()]
                    pids = [p.id_in_subsession for p in g.get_players()]

                    for perm in permutations(slots, 3):
                        tag_map = {pid: slot_tag for pid, (_, slot_tag) in zip(pids, perm)}
                        signal_map = {pid: slot_tag[0] for pid, slot_tag in tag_map.items()}

                        match_count = 0
                        for pid, tag in tag_map.items():
                            need_list = needs[pid]
                            others_signals = [sig for pid2, sig in signal_map.items() if pid2 != pid]
                            if any(pattern_match(tag, pat, others_signals) for pat in need_list):
                                match_count += 1

                        if match_count >= tier:
                            best_match = (idx, perm, rec['state'])
                            break

                    if best_match:
                        break
                if best_match:
                    break

            if not best_match:
                for idx, rec in enumerate(table):
                    if idx not in used_idx:
                        slots = [(sid, info['signals'] + info['qualities']) for sid, info in rec['players'].items()]
                        best_match = (idx, tuple(slots), rec['state'])
                        break

            idx, perm, state = best_match
            used_idx.add(idx)
            rec = table[idx]
            g.state = state
            players = g.get_players()

            for p, (sid, tag) in zip(players, perm):
                info = rec['players'][sid]
                p.state = state
                p.signals = info['signals']
                p.qualities = info['qualities']

            for p in players:
                tag = p.signals + p.qualities
                others_signals = [pl.signals for pl in players if pl != p]
                chosen = find_pattern_from_signals(tag, others_signals)
                p.current_pattern = chosen
                p.participant.vars.setdefault('patterns_seen_two', []).append(chosen)

            g._count_signals()
            for p in players:
                p.r_count = g.r_count
                p.b_count = g.b_count

        sv['used_records'] = used_idx

# 其余页面逻辑保持与原版一致 ---------------------------------------------

class Main_Instructions(Page):
    @staticmethod
    def is_displayed(player):
        return player.round_number == 1


class ResultsWaitPage1(WaitPage):
    wait_for_all_groups = True


# ------------------------------------------------------------------
#  network_and_voting —— 关键信息可见逻辑
# ------------------------------------------------------------------
class network_and_voting(Page):
    form_model  = 'player'
    form_fields = ['timeSpent', 'vote']

    @staticmethod
    def vars_for_template(player):
        """
        始终返回 3 条 row，未观察到的信息用 Unknown 填充。
        若 pattern 含 “+”，随机（且在整个回合内固定）选择一名满足右侧 tag 的 partner。
        """
        pattern   = player.current_pattern
        g_players = player.group.get_players()
        tag_map   = {p.id_in_group: p.signals + p.qualities for p in g_players}

        # ── 1) 如有 pair-pattern，确定要显示的 partner id ─────────────
        partner_id_visible = None
        if '+' in pattern:
            own_tag, partner_tag = pattern.split('+')
            partner_pool = [p.id_in_group for p in g_players
                            if p != player and tag_map[p.id_in_group] == partner_tag]

            key = f'partner_chosen_r{player.round_number}'
            if partner_pool:
                # 如果之前已经选过，就用老的；否则随机选一个存起来
                partner_id_visible = player.participant.vars.get(key)
                if partner_id_visible not in partner_pool:
                    partner_id_visible = random.choice(partner_pool)
                    player.participant.vars[key] = partner_id_visible

        # ── 2) 组装 rows，先全部 Unknown，再按可见规则“填充” ────────
        rows = []
        for gp in g_players:
            # 默认完全未知
            row = dict(
                id_in_group         = gp.id_in_group,
                is_self             = (gp == player),
                player_signal_style = '',          # 留空→模板会显示 unknown-signal
                box_info            = 'Unknown',   # strong / weak / unknown
            )

            # —— 决定是否揭示 —— #
            reveal_signal  = True
            reveal_quality = False

            if gp == player:                       # 自己
                reveal_quality = True   # solo-mixed 不透露质量
            elif partner_id_visible and gp.id_in_group == partner_id_visible:
                reveal_quality = True

            # —— 写入已知信息 —— #
            if reveal_signal:
                col = 'red' if gp.signals == 'r' else 'blue'
                row['player_signal_style'] = (
                    f'height:1.4em;width:1.4em;background-color:{col};'
                    'border-radius:50%;display:inline-block;'
                    'vertical-align:middle;margin:0 0px;')
            if reveal_quality:
                row['box_info'] = 'Box A' if gp.qualities == 'h' else 'Box B'

            rows.append(row)

        # 自己排第一
        rows.sort(key=lambda d: not d['is_self'])
        return dict(participants_info=rows)



class ResultsWaitPage3(WaitPage):
    def after_all_players_arrive(self):
        self.group.set_payoffs()


class ResultsWaitPage4(WaitPage):
    wait_for_all_groups = True


class ResultsWaitPage5(WaitPage):
    @staticmethod
    def is_displayed(player):
        return player.round_number == C.NUM_ROUNDS

    def after_all_players_arrive(self):
        rnd = random.randint(1, C.NUM_ROUNDS)
        for p in self.group.get_players():
            p.selected_round = rnd
            p.payoff = p.in_round(rnd).payoff_record
            p.participant.vars[__name__] = [int(p.payoff), rnd]


class FinalResults(Page):
    @staticmethod
    def is_displayed(player):
        return player.round_number == C.NUM_ROUNDS


# ------------------------------------------------------------------
#  Page sequence
# ------------------------------------------------------------------
page_sequence = [
    StartRoundWaitPage,
    Main_Instructions,
    ResultsWaitPage1,
    network_and_voting,
    ResultsWaitPage3,
    ResultsWaitPage4,
    ResultsWaitPage5,
    FinalResults,
]
