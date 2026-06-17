import math


def resolve_combat(agents):
    for i in range(len(agents)):
        for j in range(i + 1, len(agents)):
            a = agents[i]
            b = agents[j]

            if a.hp <= 0 or b.hp <= 0: continue
            if a.faction == b.faction: continue

            dx = a.x - b.x
            dy = a.y - b.y
            distance = math.hypot(dx, dy)

            if distance < a.radius + b.radius:
                dmg_a = a.atk * 2 if getattr(a, 'out_of_zone', False) else a.atk
                dmg_b = b.atk * 2 if getattr(b, 'out_of_zone', False) else b.atk

                if a.attack_cooldown == 0:
                    b.hp -= dmg_a
                    a.attack_cooldown = 30
                    a.ult_charge = min(100, a.ult_charge + 5)
                    b.ult_charge = min(100, b.ult_charge + 10)

                if b.attack_cooldown == 0:
                    a.hp -= dmg_b
                    b.attack_cooldown = 30
                    b.ult_charge = min(100, b.ult_charge + 5)
                    a.ult_charge = min(100, a.ult_charge + 10)

                a_immune = getattr(a, 'knockback_immune', False)
                b_immune = getattr(b, 'knockback_immune', False)

                # --- 新增：弹性墙体反射机制 ---
                a_reflect = getattr(a, 'reflects_attacker', False)
                b_reflect = getattr(b, 'reflects_attacker', False)

                rel_vx = a.vx - b.vx
                rel_vy = a.vy - b.vy
                is_approaching = (rel_vx * dx + rel_vy * dy) < 0

                if is_approaching:
                    if a_reflect and not b_reflect:
                        # a (猫) 反弹 b (敌人)。猫获得敌人的速度(正常击飞)，敌人原路弹回
                        a.vx, b.vx = b.vx, -b.vx
                        a.vy, b.vy = b.vy, -b.vy
                    elif b_reflect and not a_reflect:
                        b.vx, a.vx = a.vx, -a.vx
                        b.vy, a.vy = a.vy, -a.vy
                    elif a_reflect and b_reflect:
                        a.vx, b.vx = -a.vx, -b.vx
                        a.vy, b.vy = -a.vy, -b.vy
                    else:
                        # 正常的动量交换逻辑
                        if not a_immune and not b_immune:
                            a.vx, b.vx = b.vx, a.vx
                            a.vy, b.vy = b.vy, a.vy
                        elif a_immune and not b_immune:
                            b.vx *= -1
                            b.vy *= -1
                        elif b_immune and not a_immune:
                            a.vx *= -1
                            a.vy *= -1

                # 坐标重叠排斥处理保持正常
                if distance > 0:
                    overlap = a.radius + b.radius - distance
                    if not a_immune and not b_immune:
                        a.x += (dx / distance) * (overlap / 2)
                        a.y += (dy / distance) * (overlap / 2)
                        b.x -= (dx / distance) * (overlap / 2)
                        b.y -= (dy / distance) * (overlap / 2)
                    elif a_immune and not b_immune:
                        b.x -= (dx / distance) * overlap
                        b.y -= (dy / distance) * overlap
                    elif b_immune and not a_immune:
                        a.x += (dx / distance) * overlap
                        a.y += (dy / distance) * overlap