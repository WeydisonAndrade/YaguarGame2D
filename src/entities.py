import math
import random
import pygame
from src.config import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    GRAVITY,
    JUMP_VELOCITY,
    PLAYER_WALK_SPEED,
    PLAYER_RUN_SPEED,
    PLAYER_ATTACK_FRAMES,
    PLAYER_INVULN_FRAMES,
    BLOCK_DAMAGE_FACTOR,
    ATTACK_ACTIVE_START,
    ATTACK_ACTIVE_END,
    HITSTUN_FRAMES,
    KNOCKBACK,
    GROUND_Y,
    PLATFORMS,
    ONCA_SCALE,
)
from src.player_anim import load_player_frames


def platform_rects() -> list[pygame.Rect]:
    return [pygame.Rect(*box) for box in PLATFORMS]


def apply_gravity_and_platforms(rect: pygame.Rect, vel_y: float, on_ground: bool) -> tuple[pygame.Rect, float, bool]:
    vel_y += GRAVITY
    rect.y += int(vel_y)
    grounded = False

    if vel_y >= 0:
        feet = pygame.Rect(rect.x + 12, rect.bottom - 8, max(8, rect.width - 24), 10)
        for plat in platform_rects():
            if feet.colliderect(plat) and rect.bottom <= plat.top + 18:
                rect.bottom = plat.top + 1
                vel_y = 0
                grounded = True
                break

    if rect.bottom > GROUND_Y + 1:
        rect.bottom = GROUND_Y + 1
        vel_y = 0
        grounded = True

    rect.clamp_ip(pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT + 40))
    return rect, vel_y, grounded


class GameObject(pygame.sprite.Sprite):
    """Classe Base com Polimorfismo para Renderização e Lógica"""
    def __init__(self, x, y, image_path):
        super().__init__()
        self.image = pygame.image.load(image_path).convert_alpha()
        self.rect = self.image.get_rect(midbottom=(x, y))

    def update(self, *args):
        pass


class YaguarPlayer(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.frames = load_player_frames()
        self.image = self.frames["idle"]
        self.rect = self.image.get_rect(midbottom=(x, y))
        self.max_health = 100
        self.health = 100
        self.stamina = 100
        self.has_garra_espiritual = False
        self.facing = 1
        self.vel_y = 0
        self.on_ground = True
        self.crouching = False
        self.blocking = False
        self.attacking = False
        self.attack_timer = 0
        self.attack_cooldown = 0
        self.invuln = 0
        self.anim_tick = 0
        self.run_frame = 0
        self.queued_attack = None
        self.strike_spawned = False
        self.pending_strike = None

    @property
    def hurtbox(self) -> pygame.Rect:
        w, h = 54, 110
        return pygame.Rect(self.rect.centerx - w // 2, self.rect.bottom - h, w, h)

    def _set_pose(self, name: str) -> None:
        frame = self.frames.get(name, self.frames["idle"])
        if self.facing < 0:
            frame = pygame.transform.flip(frame, True, False)
        midbottom = self.rect.midbottom
        self.image = frame
        self.rect = self.image.get_rect(midbottom=midbottom)

    def update(self, keys, mouse_pressed):
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
        if self.invuln > 0:
            self.invuln -= 1
        if self.attacking:
            self.attack_timer -= 1
            if self.attack_timer <= 0:
                self.attacking = False

        if self.stamina < 100 and not (keys[pygame.K_LSHIFT] and not self.crouching):
            self.stamina = min(100, self.stamina + 0.28)

        if self.queued_attack and not self.attacking:
            self._begin_attack(heavy=self.queued_attack == "heavy")
            self.queued_attack = None

        self.blocking = bool(keys[pygame.K_k] or keys[pygame.K_LCTRL]) and not self.attacking
        self.crouching = bool(keys[pygame.K_s] or keys[pygame.K_DOWN]) and self.on_ground and not self.attacking

        dx = 0
        if not self.crouching and not self.blocking:
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                dx -= 1
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                dx += 1

        running = dx != 0 and not self.attacking and (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) and self.stamina > 1
        speed = PLAYER_RUN_SPEED if running else PLAYER_WALK_SPEED
        if self.attacking:
            speed *= 0.45
        if running:
            self.stamina = max(0, self.stamina - 0.35)

        if dx != 0:
            if not self.attacking:
                self.facing = 1 if dx > 0 else -1
            self.rect.x += int(dx * speed)

        want_jump = keys[pygame.K_w] or keys[pygame.K_UP] or keys[pygame.K_SPACE]
        if want_jump and self.on_ground and not self.crouching and not self.blocking and not self.attacking:
            self.vel_y = JUMP_VELOCITY
            self.on_ground = False

        self.rect, self.vel_y, self.on_ground = apply_gravity_and_platforms(self.rect, self.vel_y, self.on_ground)
        self._try_spawn_strike()

        self.anim_tick += 1
        if self.attacking:
            self._set_pose("attack")
        elif self.blocking:
            self._set_pose("defend")
        elif not self.on_ground:
            self._set_pose("jump")
        elif self.crouching:
            self._set_pose("crouch")
        elif dx != 0:
            if self.anim_tick % 8 == 0:
                self.run_frame = 1 - self.run_frame
            self._set_pose("run1" if self.run_frame == 0 else "run2")
        else:
            self._set_pose("idle")

    def queue_attack(self, heavy=False) -> None:
        if self.attack_cooldown > 0 or self.blocking:
            return
        if heavy and not self.has_garra_espiritual:
            return
        self.queued_attack = "heavy" if heavy else "light"

    def _begin_attack(self, heavy=False) -> None:
        self.attacking = True
        self.attack_timer = PLAYER_ATTACK_FRAMES
        self.attack_cooldown = 20 if heavy else 14
        self.strike_spawned = False
        self.pending_strike = None
        self.rect.x += self.facing * 10
        self._heavy = heavy

    def _try_spawn_strike(self) -> None:
        if not self.attacking or self.strike_spawned:
            return
        if ATTACK_ACTIVE_END <= self.attack_timer <= ATTACK_ACTIVE_START:
            body = self.hurtbox
            heavy = getattr(self, "_heavy", False)
            reach = 86 if heavy else 64
            height = 48
            hx = body.right - 6 if self.facing > 0 else body.left - reach + 6
            hy = body.centery - height // 2
            self.pending_strike = AttackHitbox(hx, hy, reach, height, 34 if heavy else 18)
            self.strike_spawned = True
            self.invuln = max(self.invuln, 10)

    def pop_strike(self) -> "AttackHitbox | None":
        strike = self.pending_strike
        self.pending_strike = None
        return strike

    def take_damage(self, amount: float, source_x: float | None = None) -> None:
        if self.invuln > 0:
            return
        if self.blocking:
            amount *= BLOCK_DAMAGE_FACTOR
        self.health -= amount
        if source_x is not None:
            push = -KNOCKBACK if source_x >= self.hurtbox.centerx else KNOCKBACK
            self.rect.x += push
        if not self.blocking:
            self.invuln = PLAYER_INVULN_FRAMES


class AttackHitbox(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, damage):
        super().__init__()
        self.rect = pygame.Rect(x, y, width, height)
        self.damage = damage
        self.lifetime = 8

    def update(self):
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.kill()


class BaseEnemy(GameObject):
    def __init__(self, x, y, image_path, health, speed, damage):
        super().__init__(x, y, image_path)
        self.health = health
        self.speed = speed
        self.damage = damage
        self.vel_y = 0
        self.on_ground = True
        self.stun = 0

    @property
    def hurtbox(self) -> pygame.Rect:
        w = min(120, max(56, int(self.rect.width * 0.42)))
        h = min(110, max(48, int(self.rect.height * 0.55)))
        return pygame.Rect(self.rect.centerx - w // 2, self.rect.bottom - h, w, h)

    def take_hit(self, damage: int, source_x: float) -> None:
        self.health -= damage
        self.stun = HITSTUN_FRAMES
        push = KNOCKBACK + 6 if source_x < self.hurtbox.centerx else -(KNOCKBACK + 6)
        self.rect.x += push

    def move_towards(self, target_pos):
        self.rect, self.vel_y, self.on_ground = apply_gravity_and_platforms(self.rect, self.vel_y, self.on_ground)
        if self.stun > 0:
            self.stun -= 1
            return
        dx = target_pos[0] - self.hurtbox.centerx
        if abs(dx) > 70:
            self.rect.x += int(self.speed * (1 if dx > 0 else -1))
        self.rect, self.vel_y, self.on_ground = apply_gravity_and_platforms(self.rect, self.vel_y, self.on_ground)


class SpectralJaguar(BaseEnemy):
    """Onça espectral — garras e mordidas."""
    def __init__(self, x, y):
        super().__init__(x, y, "assets/enemy_onca_spectral.png", health=140, speed=3.2, damage=16)
        self.frames = {}
        for name in ("idle", "claw", "bite"):
            raw = pygame.image.load(f"assets/onca/{name}.png").convert_alpha()
            size = (max(1, int(raw.get_width() * ONCA_SCALE)), max(1, int(raw.get_height() * ONCA_SCALE)))
            self.frames[name] = pygame.transform.smoothscale(raw, size)
        self.image = self.frames["idle"]
        self.rect = self.image.get_rect(midbottom=(x, y))
        self.facing = -1
        self.action = "idle"
        self.action_timer = 0
        self.cooldown = 20
        self.next_attack = "claw"
        self.pending_melee = None
        self.melee_spawned = False
        self.pending_damage = 16

    @property
    def hurtbox(self) -> pygame.Rect:
        w, h = int(96 * ONCA_SCALE), int(78 * ONCA_SCALE)
        return pygame.Rect(self.rect.centerx - w // 2, self.rect.bottom - h, w, h)

    def _set_pose(self, name: str) -> None:
        frame = self.frames.get(name, self.frames["idle"])
        if self.facing < 0:
            frame = pygame.transform.flip(frame, True, False)
        midbottom = self.rect.midbottom
        self.image = frame
        self.rect = self.image.get_rect(midbottom=midbottom)

    def pop_melee(self) -> pygame.Rect | None:
        box = self.pending_melee
        self.pending_melee = None
        return box

    def update(self, player_pos):
        self.facing = -1 if player_pos[0] < self.hurtbox.centerx else 1
        dist = abs(player_pos[0] - self.hurtbox.centerx)

        if self.action_timer > 0:
            self.action_timer -= 1
            pose = "claw" if self.action == "claw" else "bite"
            self._set_pose(pose)
            if not self.melee_spawned and 6 <= self.action_timer <= 14:
                reach = 88 if self.action == "claw" else 72
                hx = self.hurtbox.right - 8 if self.facing > 0 else self.hurtbox.left - reach + 8
                hy = player_pos[1] - 24
                self.pending_melee = pygame.Rect(hx, hy, reach, 50)
                self.pending_damage = 18 if self.action == "claw" else 24
                self.melee_spawned = True
                if self.action == "bite":
                    self.rect.x += self.facing * 18
            if self.action_timer <= 0:
                self.action = "idle"
                self.cooldown = 28
            self.rect, self.vel_y, self.on_ground = apply_gravity_and_platforms(self.rect, self.vel_y, self.on_ground)
            return

        if self.cooldown > 0:
            self.cooldown -= 1

        if self.stun <= 0 and self.cooldown <= 0 and dist < 130:
            self.action = self.next_attack
            self.next_attack = "bite" if self.next_attack == "claw" else "claw"
            self.action_timer = 26
            self.melee_spawned = False

        self._set_pose("idle")
        self.move_towards(player_pos)


class OncaNegraMiniBoss(SpectralJaguar):
    """Alias antigo — a onça espectral assume este papel."""
    pass


class TreeTrunk(pygame.sprite.Sprite):
    """Tronco arremessado pelo Mapinguari em direção ao alvo."""
    def __init__(self, x, y, target: tuple[float, float]):
        super().__init__()
        raw = pygame.image.load("assets/tree_trunk.png").convert_alpha()
        dx = target[0] - x
        dy = target[1] - y
        dist = math.hypot(dx, dy) or 1.0
        speed = 10.5
        self.vx = speed * dx / dist
        self.vy = speed * dy / dist
        angle = -math.degrees(math.atan2(self.vy, self.vx))
        self.image = pygame.transform.rotate(raw, angle)
        self.fx = float(x)
        self.fy = float(y)
        self.rect = self.image.get_rect(center=(int(self.fx), int(self.fy)))
        self.damage = 22
        self.life = 160

    def update(self, *args):
        self.fx += self.vx
        self.fy += self.vy
        self.rect.center = (int(self.fx), int(self.fy))
        self.life -= 1
        if (
            self.life <= 0
            or self.rect.right < -40
            or self.rect.left > SCREEN_WIDTH + 40
            or self.rect.bottom < -40
            or self.rect.top > SCREEN_HEIGHT + 40
        ):
            self.kill()


class MapinguariBoss(BaseEnemy):
    """Boss Final — garras e arremesso de troncos."""
    def __init__(self, x, y):
        super().__init__(x, y, "assets/boss_mapinguari.png", health=320, speed=1.3, damage=22)
        self.frames = {
            "idle": pygame.image.load("assets/mapinguari/idle.png").convert_alpha(),
            "attack": pygame.image.load("assets/mapinguari/attack.png").convert_alpha(),
            "throw": pygame.image.load("assets/mapinguari/throw.png").convert_alpha(),
        }
        self.image = self.frames["idle"]
        self.rect = self.image.get_rect(midbottom=(x, y))
        self.phase = 1
        self.facing = -1
        self.action = "idle"
        self.action_timer = 0
        self.cooldown = 40
        self.pending_melee = None
        self.pending_log = None
        self.melee_spawned = False
        self.log_spawned = False
        self.aim = (x, y)

    @property
    def hurtbox(self) -> pygame.Rect:
        w, h = 110, 190
        return pygame.Rect(self.rect.centerx - w // 2, self.rect.bottom - h, w, h)

    def _set_pose(self, name: str) -> None:
        frame = self.frames.get(name, self.frames["idle"])
        if self.facing < 0:
            frame = pygame.transform.flip(frame, True, False)
        midbottom = self.rect.midbottom
        self.image = frame
        self.rect = self.image.get_rect(midbottom=midbottom)

    def pop_melee(self) -> pygame.Rect | None:
        box = self.pending_melee
        self.pending_melee = None
        return box

    def pop_log(self) -> TreeTrunk | None:
        log = self.pending_log
        self.pending_log = None
        return log

    def _hand_throw_point(self) -> tuple[int, int]:
        """Ponto das mãos no alto da pose de arremesso (não a boca da barriga)."""
        hx = self.rect.centerx + self.facing * int(self.rect.width * 0.36)
        hy = self.rect.top + int(self.rect.height * 0.16)
        return hx, hy

    def update(self, player_pos):
        if self.health < 100:
            self.phase = 3
            self.speed = 2.2
        elif self.health < 200:
            self.phase = 2
            self.speed = 1.7

        self.aim = player_pos
        if self.action == "idle":
            self.facing = -1 if player_pos[0] < self.hurtbox.centerx else 1
        dist = abs(player_pos[0] - self.hurtbox.centerx)

        if self.action_timer > 0:
            self.action_timer -= 1
            if self.action == "attack":
                self._set_pose("attack")
                if not self.melee_spawned and 8 <= self.action_timer <= 16:
                    reach = 110
                    hx = self.hurtbox.right if self.facing > 0 else self.hurtbox.left - reach
                    hy = self.aim[1] - 28
                    self.pending_melee = pygame.Rect(hx, hy, reach, 56)
                    self.melee_spawned = True
            elif self.action == "throw":
                self._set_pose("throw")
                if not self.log_spawned and self.action_timer <= 10:
                    hx, hy = self._hand_throw_point()
                    self.pending_log = TreeTrunk(hx, hy, self.aim)
                    self.log_spawned = True
            if self.action_timer <= 0:
                self.action = "idle"
                self.cooldown = 36 if self.phase == 1 else 24
            self.rect, self.vel_y, self.on_ground = apply_gravity_and_platforms(self.rect, self.vel_y, self.on_ground)
            return

        if self.cooldown > 0:
            self.cooldown -= 1

        if self.stun <= 0 and self.cooldown <= 0:
            if dist < 150:
                self.action = "attack"
                self.action_timer = 28
                self.melee_spawned = False
                self.facing = -1 if player_pos[0] < self.hurtbox.centerx else 1
            elif dist > 170:
                self.action = "throw"
                self.action_timer = 42
                self.log_spawned = False
                self.facing = -1 if player_pos[0] < self.hurtbox.centerx else 1

        if self.action == "idle":
            self._set_pose("idle")
            self.move_towards(player_pos)


class HerbItem(GameObject):
    def __init__(self, x, y):
        super().__init__(x, y, "assets/herb.png")
