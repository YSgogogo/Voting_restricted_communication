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
    NAME_IN_URL       = 'A_Voting_four'
    PLAYERS_PER_GROUP = 3
    NUM_ROUNDS        = 10
    AMOUNT_CORRECT    = 2
    CHOICES           = [('R', 'RED Box'), ('B', 'BLUE Box')]
    STATES            = ['R', 'B']
    QUALITIES         = ['h', 'l']


# ------------------------------------------------------------------
# build pre-generated signal table
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

    def _count_signals(self):
        """组内 r / b 信号计数（用于显示）。"""
        self.r_count = sum(1 for p in self.get_players() if p.signals == 'r')
        self.b_count = C.PLAYERS_PER_GROUP - self.r_count

    def set_payoffs(self):
        correct = sum(1 for p in self.get_players() if p.vote == self.state)
        payoff = correct * C.AMOUNT_CORRECT
        for p in self.get_players():
            p.payoff_record = payoff      # 存到中间变量；最后一页再抽一轮兑现


# ------------------------------------------------------------------
#  Player
# ------------------------------------------------------------------
class Player(BasePlayer):
    # —— 计时 ——————————————————————————
    timeSpent1 = models.FloatField()
    timeSpent2 = models.FloatField()

    # —— 决策 ——————————————————————————
    send_decision   = models.StringField()
    vote            = models.StringField(widget=widgets.RadioSelect,
                                         choices=C.CHOICES)

    # —— 私有信息 ————————————————————
    state     = models.StringField()
    signals   = models.CharField()
    qualities = models.StringField()

    # —— 信息网络 & 记录 ———————————
    info_from_whom  = models.StringField(initial='')  # “1,3” 这样的 id 列表
    info_codes      = models.StringField(initial='')  # “Rh,Wb” 形式
    role_in_lottery = models.StringField(initial='none')
    payoff_record   = models.IntegerField(initial=0)
    selected_round  = models.IntegerField()

    # 显示用
    r_count        = models.IntegerField()
    b_count        = models.IntegerField()
    current_pattern = models.StringField()            # 本轮实际分配的 pattern

    # —— 页面动态选项 ——————————————————
    def send_decision_choices(player):
        others = [p.signals for p in player.group.get_players() if p != player]
        if others[0] == others[1]:
            col  = 'R' if others[0] == 'r' else 'B'
            opts = [f'send to one of group members who got {col}',
                    'send to all group members',
                    'do not send to anyone']
        else:
            opts = ['send to a group member who got R',
                    'send to a group member who got B',
                    'send to all group members',
                    'do not send to anyone']
        random.shuffle(opts)
        return opts


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
                seen = p.participant.vars.get('patterns_seen_four', [])
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
                p.participant.vars.setdefault('patterns_seen_four', []).append(chosen)

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


class Info_and_decision(Page):
    form_model  = 'player'
    form_fields = ['timeSpent1', 'send_decision']

    @staticmethod
    def vars_for_template(player):
        my_quality = 'strong source' if player.qualities == 'h' else 'weak source'

        col = 'red' if player.signals == 'r' else 'blue'
        my_signal  = (
            f'height:1.4em;width:1.4em;background-color:{col};'
            'border-radius:50%;display:inline-block;'
            'vertical-align:middle;margin:0 0px;')

        others   = []
        for p in player.group.get_players():
            if p == player:
                continue

            quality = ('strong source' if p.qualities == 'h' else 'weak source') \
                    if str(p.id_in_group) in player.info_from_whom.split(',') \
                    else 'Unknown jar'
            col = 'red' if p.signals == 'r' else 'blue'
            signal = (
                f'height:1.4em;width:1.4em;background-color:{col};'
                'border-radius:50%;display:inline-block;'
                'vertical-align:middle;margin:0 0px;')

            others.append(dict(id=p.id_in_group, signal = signal, quality_label=quality))
        return dict( my_quality=my_quality, my_signal = my_signal,
                    my_id=player.id_in_group, other_urns=others)


class ResultsWaitPage2(WaitPage):
    wait_for_all_groups = True

    def after_all_players_arrive(self):
        for g in self.subsession.get_groups():
            ps = g.get_players()

            # 初始：每人只“知道自己”
            for p in ps:
                p.info_from_whom = str(p.id_in_group)
                p.role_in_lottery = 'none'

            chosen = random.choice(ps)
            role   = random.choice(['sender'])
            chosen.role_in_lottery = role

            if role == 'sender' and 'do not send' not in chosen.send_decision:
                if 'send to all group members' in chosen.send_decision:
                    # 将 chosen 的 id 发给所有除自己外的组员
                    for rec in ps:
                        if rec != chosen:
                            rec.info_from_whom += f',{chosen.id_in_group}'
                else:
                    tgt = 'r' if 'got R' in chosen.send_decision else 'b'
                    cand = [x for x in ps if x != chosen and x.signals == tgt]
                    if cand:
                        rec = random.choice(cand)
                        rec.info_from_whom += f',{chosen.id_in_group}'


            # 把收到的 id 列表翻译成 “Rh, Wb” 形式便于显示
            for p in ps:
                codes = []
                for src_id in map(int, p.info_from_whom.split(',')):
                    src = next(x for x in ps if x.id_in_group == src_id)
                    sig = 'R' if src.signals == 'r' else 'B'
                    codes.append(f'{sig}{src.qualities}')
                p.info_codes = ','.join(codes)


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

            player_signal_style = f"height: 1.2em; width: 1.2em; background-color: {player_signal_color}; border-radius: 50%; display: inline-block; vertical-align: middle; margin: 0 5px;"
            all_info = participant.info_from_whom

            if participant.qualities == 'l':
                quality_representation = "weak"
            else:
                quality_representation = "strong"

            box_info = quality_representation if participant.id_in_group in info_sources else 'Unknown'

            participants_info.append({
                'id_in_group': participant.id_in_group,
                'quality_representation': quality_representation,
                'player_signal_style': player_signal_style,
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
    Info_and_decision,
    ResultsWaitPage2,
    network_and_voting,
    ResultsWaitPage3,
    ResultsWaitPage4,
    ResultsWaitPage5,
    FinalResults,
]
