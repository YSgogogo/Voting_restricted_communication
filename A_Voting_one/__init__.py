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
    NAME_IN_URL       = 'A_Voting_one'
    PLAYERS_PER_GROUP = 3
    NUM_ROUNDS        = 10
    AMOUNT_CORRECT    = 6
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

        for p in self.get_players():
            p.payoff_record = C.AMOUNT_CORRECT if p.vote == self.state else 0


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
# ------------------------------------------------------------------
class StartRoundWaitPage(WaitPage):
    wait_for_all_groups = True

    def after_all_players_arrive(self):

        self.subsession.group_randomly()

        sv = self.session.vars
        if 'signal_table' not in sv:
            sv['signal_table'] = build_signal_table(1000)
            sv['used_records'] = set()

        table    = sv['signal_table']
        used_idx = sv['used_records']

        # 2) 定义每名玩家需要经历的所有 pattern
        rounds_req = {
            'solo': ['rh', 'rl', 'bh', 'bl', 'rh_rl', 'bh_bl'],
            'pair': ['rh+bh', 'bh+rh', 'rl+bl', 'bl+rl'],
        }

        # pattern 匹配助手
        def pattern_match(slot_tag: str, pattern: str) -> bool:
            if '+' in pattern:
                return slot_tag in pattern.split('+')
            if '_' in pattern:
                return slot_tag in pattern.split('_')
            return slot_tag == pattern

        # 3) 对每个分组挑一条未用记录
        for g in self.subsession.get_groups():

            # 3.1 算出每位玩家还缺哪些 pattern
            needs = {}
            for p in g.get_players():
                seen = p.participant.vars.get('patterns_seen_one', [])
                solo_seen = [x for x in seen if '+' not in x]
                pair_seen = [x for x in seen if '+' in x]
                need_solo = [x for x in rounds_req['solo'] if x not in solo_seen]
                need_pair = [x for x in rounds_req['pair'] if x not in pair_seen]
                needs[p.id_in_subsession] = need_solo + need_pair

            # 3.2 遍历 signal_table：保留能让“最多人立即兑现 pair-pattern”的记录
            best_match      = None  # (idx, perm, state)
            best_pair_count = -1

            for idx, rec in enumerate(table):
                if idx in used_idx:
                    continue

                slots = [(sid, info['signals'] + info['qualities'])
                         for sid, info in rec['players'].items()]
                pids  = [p.id_in_subsession for p in g.get_players()]

                for perm in permutations(slots, 3):
                    tag_map  = {pid: slot_tag for pid, (_, slot_tag) in zip(pids, perm)}
                    all_tags = [t for _, t in perm]

                    valid = True
                    pair_cnt = 0
                    for pid, tag in tag_map.items():
                        need_list = needs[pid]

                        # 必须能满足至少一个需求
                        if not any(pattern_match(tag, pat) for pat in need_list):
                            valid = False
                            break

                        # 若玩家还缺某条 pair-pattern 且另一端 tag 存在，则 +1
                        if any('+' in pat and pat.split('+')[0] == tag
                               and pat.split('+')[1] in all_tags for pat in need_list):
                            pair_cnt += 1

                    if valid and pair_cnt > best_pair_count:
                        best_match      = (idx, perm, rec['state'])
                        best_pair_count = pair_cnt
                        if best_pair_count == 3:   # 已经最优
                            break
                if best_pair_count == 3:
                    break

            # 3.3 如果完全找不到满足需求的记录，就随机挑一条
            if not best_match:
                for idx, rec in enumerate(table):
                    if idx not in used_idx:
                        slots = [(sid, info['signals'] + info['qualities'])
                                 for sid, info in rec['players'].items()]
                        best_match = (idx, tuple(slots), rec['state'])
                        break

            # 3.4 把记录正式分配给本组
            idx, perm, state = best_match
            used_idx.add(idx)
            rec        = table[idx]
            g.state    = state
            players    = g.get_players()
            all_tags   = [info['signals'] + info['qualities']
                          for info in rec['players'].values()]

            # ── 基础字段 ───────────────────
            for p, (sid, tag) in zip(players, perm):
                info        = rec['players'][sid]
                p.state     = state
                p.signals   = info['signals']
                p.qualities = info['qualities']

            # ── 逐人挑选 current_pattern ──
            for p in players:
                tag       = p.signals + p.qualities
                need_list = needs[p.id_in_subsession]

                pair_opts = [pat for pat in need_list
                             if '+' in pat
                             and pat.split('+')[0] == tag
                             and pat.split('+')[1] in all_tags]

                if pair_opts:
                    chosen = pair_opts[0]
                else:
                    solo_opts = [pat for pat in need_list
                                 if '+' not in pat and pattern_match(tag, pat)]
                    chosen = solo_opts[0] if solo_opts else need_list[0]

                p.current_pattern = chosen
                p.participant.vars.setdefault('patterns_seen_one', []).append(chosen)

            # ── 更新 r / b 计数 ─────────────
            g._count_signals()
            for p in players:
                p.r_count = g.r_count
                p.b_count = g.b_count

        # 4) 写回 used_records
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
            reveal_signal  = False
            reveal_quality = False

            if gp == player:                       # 自己
                reveal_signal = True
                reveal_quality = ('_' not in pattern)   # solo-mixed 不透露质量
            elif partner_id_visible and gp.id_in_group == partner_id_visible:
                reveal_signal = True
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
