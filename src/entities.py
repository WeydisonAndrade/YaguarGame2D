"""Entidades da Fase 1: Yáguar, onça espectral, Mapinguari, tronco e erva.

A física de chão é compartilhada (gravidade + laje). O combate usa hurtboxes
menores que o sprite, para o corpo não coincidir com folhas e penas.
"""
import math
import random
from pathlib import Path
import pygame
from src import audio
from src.config import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    GRAVITY,
    JUMP_VELOCITY,
    PLAYER_WALK_SPEED,
    PLAYER_RUN_SPEED,
    PLAYER_ATTACK_FRAMES,
    SPEAR_ROAR_EVERY,
    PLAYER_INVULN_FRAMES,
    BLOCK_DAMAGE_FACTOR,
    BLOCK_RECOVERY_FRAMES,
    ATTACK_ACTIVE_START,
    ATTACK_ACTIVE_END,
    HITSTUN_FRAMES,
    KNOCKBACK,
    GROUND_Y,
    PLATFORMS,
    ONCA_SCALE,
    ONCA_WALK_SPEED,
    ONCA_RUN_SPEED,
    ONCA_RUN_DISTANCE,
    KEY_BOW_AIM,
    KEY_ATTACK,
    MOUSE_ATTACK_HELD,
    BOW_AIM_SPEED,
    BOW_MAX_CHARGE,
    BOW_NOCK,
    BOW_RECOVER,
    BOW_MIN_SPEED,
    BOW_MAX_SPEED,
    BOW_GRAVITY,
    BOW_DAMAGE_MIN,
    BOW_DAMAGE_MAX,
    BOW_WEAK_MULT,
    BOW_LIFETIME,
    BOW_STUCK_TIME,
    FPS,
)
from src.color_profile import using_raw_bow_color
from src.player_anim import load_player_frames, POSE_ANCHORS, RAW_BOW_SURFACES


_world_platforms = PLATFORMS
_world_width = SCREEN_WIDTH
_allow_pits = False


def set_physics_world(platforms: tuple, width: int, allow_pits: bool = False) -> None:
    """Troca a laje da arena pela clareira (fossos) ou devolve o chão contínuo."""
    global _world_platforms, _world_width, _allow_pits
    _world_platforms = platforms
    _world_width = width
    _allow_pits = allow_pits


def platform_rects() -> list[pygame.Rect]:
    """Converte as plataformas ativas em retângulos de colisão."""
    return [pygame.Rect(*box) for box in _world_platforms]


def apply_gravity_and_platforms(rect: pygame.Rect, vel_y: float, on_ground: bool) -> tuple[pygame.Rect, float, bool]:
    """Aplica gravidade, pousa na laje e limita o corpo ao mundo ativo."""
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

    if not _allow_pits and rect.bottom > GROUND_Y + 1:
        rect.bottom = GROUND_Y + 1
        vel_y = 0
        grounded = True

    if rect.left < 0:
        rect.left = 0
    if rect.right > _world_width:
        rect.right = _world_width
    # Na clareira as falésias ficam no meio da pintura: o salto (teto ~137 px)
    # entra no dossel. Cortar o topo anularia o pulo sem mudar a física.
    if not _allow_pits:
        if rect.top < 0:
            rect.top = 0
            if vel_y < 0:
                vel_y = 0
    return rect, vel_y, grounded


def _scale_onca_frame(raw: pygame.Surface) -> pygame.Surface:
    size = (max(1, int(raw.get_width() * ONCA_SCALE)), max(1, int(raw.get_height() * ONCA_SCALE)))
    return pygame.transform.smoothscale(raw, size)


def _pose_from_base(base: pygame.Surface, sx: float, sy: float) -> pygame.Surface:
    w = max(1, int(base.get_width() * sx))
    h = max(1, int(base.get_height() * sy))
    return pygame.transform.smoothscale(base, (w, h))


_ARROW_SURF: pygame.Surface | None = None


def _arrow_image() -> pygame.Surface:
    """Flecha isolada no estilo do trigger01, na escala do personagem."""
    global _ARROW_SURF
    from src import player_anim

    if player_anim.SCALED_ARROW is not None:
        return player_anim.SCALED_ARROW
    if _ARROW_SURF is not None:
        return _ARROW_SURF
    for path in (Path("assets/player/arrow_color_corrected.png"), Path("assets/player/arrow.png")):
        if path.is_file():
            _ARROW_SURF = pygame.image.load(str(path)).convert_alpha()
            return _ARROW_SURF
    surf = pygame.Surface((34, 12), pygame.SRCALPHA)
    pygame.draw.polygon(surf, (214, 208, 190), [(0, 3), (5, 6), (0, 9)])
    pygame.draw.rect(surf, (118, 74, 32), (4, 4, 20, 4))
    pygame.draw.rect(surf, (168, 122, 58), (5, 5, 18, 2))
    pygame.draw.polygon(surf, (196, 196, 204), [(22, 1), (34, 6), (22, 11)])
    pygame.draw.polygon(surf, (150, 150, 158), [(22, 3), (30, 6), (22, 9)])
    _ARROW_SURF = surf
    return surf


# Empunhadura do arco pintado no sprite (facing direita), relativa aos pés (midbottom).
# Medido nos PNGs de assets/player — a flecha sai deste ponto, não de um overlay.
BOW_HAND_OFFSET = {
    "idle": (20.0, -95.0),
    "run1": (30.0, -90.0),
    "run2": (26.0, -90.0),
    "jump": (28.0, -74.0),
    "crouch": (32.0, -68.0),
    "defend": (22.0, -94.0),
    "attack": (28.0, -110.0),
    "bow": (96.5, -129.0),
    "bow_nock": (88.0, -118.0),
    "bow_quiver": (70.0, -110.0),
}


def _aim_from_gamepad(origin: tuple[float, float]) -> tuple[float, float] | None:
    """Analógico direito, se houver controle. None se não houver ou estiver no morto."""
    try:
        if not pygame.joystick.get_init():
            pygame.joystick.init()
        if pygame.joystick.get_count() <= 0:
            return None
        pad = pygame.joystick.Joystick(0)
        if pad.get_numaxes() < 4:
            return None
        rx, ry = pad.get_axis(2), pad.get_axis(3)
        if math.hypot(rx, ry) < 0.32:
            return None
        return origin[0] + rx * 260.0, origin[1] + ry * 260.0
    except pygame.error:
        return None


class GameObject(pygame.sprite.Sprite):
    """Sprite simples com imagem e âncora no midbottom (pés no chão)."""

    def __init__(self, x, y, image_path):
        super().__init__()
        self.image = pygame.image.load(image_path).convert_alpha()
        self.rect = self.image.get_rect(midbottom=(x, y))

    def update(self, *args):
        pass


class YaguarPlayer(pygame.sprite.Sprite):
    """Protagonista: andar, correr, pular, agachar, bloquear, lança e arco."""

    def __init__(self, x, y):
        super().__init__()
        self.frames = load_player_frames()
        self.image = self.frames["idle"]
        self.rect = self.image.get_rect(midbottom=(x, y))
        self.max_health = 100
        self.health = 100
        self.max_stamina = 100
        self.stamina = 100
        self.has_garra_espiritual = False  # Liberada após a terceira onça
        self.facing = 1
        self.vel_y = 0
        self.on_ground = True
        self.air_state = "grounded"
        self.checkpoint = (x, y)
        self.safe_feet = (x, y)
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
        self.flash_timer = 0
        self.flash_color = (255, 255, 255)
        self._heavy = False
        self.spear_attacks = 0  # Conta golpes de lança para o rugido a cada SPEAR_ROAR_EVERY
        self.spear_magic = 0    # Frames de encantamento da lança após o rugido
        self._roar_fx = False
        self._jump_held = False
        # Arco — estados na mesma máquina (None, nock, aim, draw, shoot, recover)
        self.bow_state = None
        self.bow_charge = 0.0
        self.bow_recover = 0.0
        self.bow_nock = 0.0
        self.aim_angle = 0.0
        self.aim_world = (float(x), float(y))
        self.camera_x = 0.0
        self.pending_arrow = None
        self.arrow_ammo = None  # None = ilimitado (protótipo)
        self._bow_fire_held = False
        self._bow_need_release = False
        self._pose_name = "idle"

    @property
    def hurtbox(self) -> pygame.Rect:
        """Caixa de dano do tronco, menor que o sprite (arco e penas ficam de fora)."""
        w, h = 54, 110
        return pygame.Rect(self.rect.centerx - w // 2, self.rect.bottom - h, w, h)

    def _set_pose(self, name: str) -> None:
        """Troca o frame e espelha se estiver virado para a esquerda, mantendo os pés."""
        self._pose_name = name if name in self.frames else "idle"
        if using_raw_bow_color() and self._pose_name in RAW_BOW_SURFACES:
            frame = RAW_BOW_SURFACES[self._pose_name]
        else:
            frame = self.frames.get(self._pose_name, self.frames["idle"])
        if self.facing < 0:
            frame = pygame.transform.flip(frame, True, False)
        midbottom = self.rect.midbottom
        self.image = frame
        self.rect = self.image.get_rect(midbottom=midbottom)

    def update(self, keys, mouse_pressed, dt: float = 1.0 / FPS):
        dt = max(1e-4, min(0.05, float(dt)))
        # Timers de cooldown, invulnerabilidade e duração do golpe
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
        if self.invuln > 0:
            self.invuln -= 1
        if self.attacking:
            self.attack_timer -= 1
            if self.attack_timer <= 0:
                self.attacking = False

        fire_held = bool(mouse_pressed[MOUSE_ATTACK_HELD] if mouse_pressed else False) or bool(keys[KEY_ATTACK])
        # A/D viram antes do arco, para o disparo sair no lado certo no mesmo quadro.
        if not self.attacking:
            left = bool(keys[pygame.K_a] or keys[pygame.K_LEFT])
            right = bool(keys[pygame.K_d] or keys[pygame.K_RIGHT])
            if left and not right:
                self.facing = -1
            elif right and not left:
                self.facing = 1
        self._update_bow(keys, fire_held, dt)

        # Recupera fôlego quando não está sprintando
        if self.stamina < self.max_stamina and not (keys[pygame.K_LSHIFT] and not self.crouching):
            self.stamina = min(self.max_stamina, self.stamina + 0.28)

        if self.queued_attack and not self.attacking and not self.bow_state:
            self._begin_attack(heavy=self.queued_attack == "heavy")
            self.queued_attack = None
        elif self.queued_attack and self.bow_state:
            self.queued_attack = None

        aiming = self.bow_state in ("nock", "aim", "draw")
        self.blocking = (
            bool(keys[pygame.K_k] or keys[pygame.K_LCTRL])
            and not self.attacking
            and not self.bow_state
        )
        self.crouching = (
            bool(keys[pygame.K_s] or keys[pygame.K_DOWN])
            and self.on_ground
            and not self.attacking
            and not aiming
        )

        # Movimento horizontal: A/D ou setas; Shift corre e gasta stamina
        dx = 0
        if not self.crouching and not self.blocking:
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                dx -= 1
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                dx += 1

        running = (
            dx != 0
            and not self.attacking
            and not aiming
            and (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT])
            and self.stamina > 1
        )
        speed = PLAYER_RUN_SPEED if running else PLAYER_WALK_SPEED
        if self.attacking:
            speed *= 0.45
        if aiming:
            speed *= BOW_AIM_SPEED
        if self.bow_state in ("shoot", "recover"):
            speed *= 0.28
        if running:
            self.stamina = max(0, self.stamina - 0.35)

        want_jump = keys[pygame.K_w] or keys[pygame.K_UP] or keys[pygame.K_SPACE]
        self._jump_held = bool(want_jump)

        if dx != 0:
            if not self.attacking:
                self.facing = 1 if dx > 0 else -1
            self.rect.x += int(dx * speed)
        if (
            want_jump
            and self.on_ground
            and not self.crouching
            and not self.blocking
            and not self.attacking
            and self.bow_state not in ("shoot", "recover")
        ):
            self.vel_y = JUMP_VELOCITY
            self.on_ground = False

        self.rect, self.vel_y, self.on_ground = apply_gravity_and_platforms(self.rect, self.vel_y, self.on_ground)
        if self.on_ground:
            self.air_state = "grounded"
            self.safe_feet = (self.rect.centerx, self.rect.bottom)
        elif self.vel_y < 0:
            self.air_state = "jumping"
        else:
            self.air_state = "falling"
        self._try_spawn_strike()

        # Pose visual: Q saca a flecha da aljava, encaixa e só então puxa a corda.
        self.anim_tick += 1
        if self.bow_state:
            self._set_pose(self._bow_pose_name())
        elif self.attacking:
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
        """Enfileira lança (leve) ou Garra Espiritual (pesado, se desbloqueada)."""
        if self.attack_cooldown > 0 or self.blocking or self.bow_state:
            return
        if heavy and not self.has_garra_espiritual:
            return
        self.queued_attack = "heavy" if heavy else "light"

    def _on_vine(self) -> bool:
        return bool(getattr(self, "on_vine", False) or getattr(self, "swinging", False))

    def _refresh_aim(self, keys=None) -> None:
        """O tiro segue o lado para o qual Yáguar está virado (A/D), não o mouse."""
        mx, my = pygame.mouse.get_pos()
        cam = float(getattr(self, "camera_x", 0) or 0)
        world = (mx + cam, float(my))
        hand = self.bow_anchor()
        pad = _aim_from_gamepad(hand)
        if pad is not None:
            world = pad
            dx = pad[0] - hand[0]
            if abs(dx) > 40:
                self.facing = 1 if dx > 0 else -1
        self.aim_world = world

        if keys is not None:
            left = bool(keys[pygame.K_a] or keys[pygame.K_LEFT])
            right = bool(keys[pygame.K_d] or keys[pygame.K_RIGHT])
            if left and not right:
                self.facing = -1
            elif right and not left:
                self.facing = 1
        self.aim_angle = 0.0 if self.facing > 0 else math.pi

    def bow_anchor(self) -> tuple[float, float]:
        """Ponta da flecha na pose atual do arco, ou empunhadura nas outras poses."""
        pose = self._bow_pose_name() if self.bow_state else getattr(self, "_pose_name", "idle")
        ox, oy = POSE_ANCHORS.get(pose) or BOW_HAND_OFFSET.get(pose, BOW_HAND_OFFSET["idle"])
        return self.rect.centerx + ox * self.facing, self.rect.bottom + oy

    def arrow_spawn(self) -> tuple[float, float]:
        """A flecha sai da ponta da que ele já segura na pose."""
        return self.bow_anchor()

    def _cancel_bow(self) -> None:
        self.bow_state = None
        self.bow_charge = 0.0
        self.bow_recover = 0.0
        self.bow_nock = 0.0
        self._bow_fire_held = False

    def _begin_nock(self) -> None:
        """Tira a flecha da aljava e encaixa na corda antes de mirar."""
        if "bow_quiver" in self.frames or "bow_nock" in self.frames:
            self.bow_state = "nock"
            self.bow_nock = BOW_NOCK
            self.bow_charge = 0.0
            return
        self.bow_state = "aim"
        self.bow_nock = 0.0
        self.bow_charge = 0.0

    def _bow_pose_name(self) -> str:
        """Frame do arco: aljava → nock → corda puxada."""
        if self.bow_state == "nock":
            if self.bow_nock > BOW_NOCK * 0.5 and "bow_quiver" in self.frames:
                return "bow_quiver"
            if "bow_nock" in self.frames:
                return "bow_nock"
        elif self.bow_state == "aim" and "bow_nock" in self.frames:
            return "bow_nock"
        if "bow" in self.frames:
            return "bow"
        return "idle"

    def _update_bow(self, keys, fire_held: bool, dt: float) -> None:
        want_aim = bool(keys[KEY_BOW_AIM]) and self.health > 0
        if self._on_vine() or self.attacking:
            if self.bow_state in ("nock", "aim", "draw"):
                self._cancel_bow()
            return

        if self.bow_state in ("shoot", "recover"):
            self.bow_recover -= dt
            if self.bow_state == "shoot" and self.bow_recover <= BOW_RECOVER * 0.55:
                self.bow_state = "recover"
            if self.bow_recover <= 0:
                if want_aim:
                    self._begin_nock()
                else:
                    self.bow_state = None
                self.bow_charge = 0.0
            if want_aim:
                self._refresh_aim(keys)
            return

        if not want_aim:
            if self.bow_state in ("nock", "aim", "draw"):
                self._cancel_bow()
            return

        self._refresh_aim(keys)
        if self.bow_state is None:
            self._begin_nock()
            self._bow_need_release = fire_held
            self._bow_fire_held = fire_held
            return

        if self.bow_state == "nock":
            self.bow_nock -= dt
            if self._bow_need_release and not fire_held:
                self._bow_need_release = False
            self._bow_fire_held = fire_held
            if self.bow_nock <= 0:
                self.bow_state = "aim"
                self.bow_charge = 0.0
            return

        if self._bow_need_release:
            if not fire_held:
                self._bow_need_release = False
            fire_held = False

        if fire_held:
            self.bow_state = "draw"
            self.bow_charge = min(1.0, self.bow_charge + dt / BOW_MAX_CHARGE)
        elif self._bow_fire_held and self.bow_state in ("aim", "draw"):
            self._release_arrow()
        else:
            self.bow_state = "aim"
        self._bow_fire_held = fire_held

    def _release_arrow(self) -> None:
        if self.pending_arrow is not None:
            return
        if self.arrow_ammo is not None:
            if self.arrow_ammo <= 0:
                self.bow_state = "aim"
                self.bow_charge = 0.0
                return
            self.arrow_ammo -= 1
        charge = max(0.0, min(1.0, self.bow_charge))
        speed = BOW_MIN_SPEED + charge * (BOW_MAX_SPEED - BOW_MIN_SPEED)
        damage = int(round(BOW_DAMAGE_MIN + charge * (BOW_DAMAGE_MAX - BOW_DAMAGE_MIN)))
        sx, sy = self.arrow_spawn()
        sx += math.cos(self.aim_angle) * 6.0
        sy += math.sin(self.aim_angle) * 6.0
        self.pending_arrow = Arrow(sx, sy, self.aim_angle, speed, damage, owner="player")
        self.rect.x -= self.facing * 4
        self.bow_state = "shoot"
        self.bow_recover = BOW_RECOVER
        self.bow_charge = 0.0
        self._bow_need_release = True
        audio.play_bow_release()

    def pop_arrow(self) -> "Arrow | None":
        arrow = self.pending_arrow
        self.pending_arrow = None
        return arrow

    def trajectory_preview(self, steps: int = 7, step_dt: float = 0.045) -> list[tuple[float, float]]:
        """Pontos discretos da queda inicial — só para debug."""
        charge = max(0.0, min(1.0, self.bow_charge))
        speed = BOW_MIN_SPEED + charge * (BOW_MAX_SPEED - BOW_MIN_SPEED)
        x, y = self.arrow_spawn()
        vx = math.cos(self.aim_angle) * speed
        vy = math.sin(self.aim_angle) * speed
        pts = []
        for _ in range(steps):
            vy += BOW_GRAVITY * step_dt
            x += vx * step_dt
            y += vy * step_dt
            pts.append((x, y))
        return pts

    def draw_bow(self, screen: pygame.Surface, offset: tuple[float, float]) -> None:
        """A pose de tiro já traz arco e flecha; não desenha um segundo conjunto."""
        return

    def draw_reticle(self, screen: pygame.Surface, cam_x: float, offset: tuple[float, float]) -> None:
        if self.bow_state not in ("aim", "draw"):
            return
        ox, oy = offset
        wx, wy = self.aim_world
        cx, cy = int(wx + ox), int(wy + oy)
        color = (242, 214, 132)
        pygame.draw.circle(screen, color, (cx, cy), 4, 1)
        pygame.draw.circle(screen, color, (cx, cy), 1)

    def roar(self) -> None:
        """Rugido do guerreiro: encanta a lança com brilho espiritual."""
        audio.play_yaguar_roar()
        self.spear_magic = 56
        self.flash_timer = max(self.flash_timer, 14)
        self.flash_color = (255, 228, 140)
        self._roar_fx = True

    def spear_axis(self) -> tuple[tuple[float, float], tuple[float, float]]:
        """Ponta da lança (mão → ponta), alinhada ao sprite e à direção."""
        body = self.hurtbox
        if self.attacking:
            hand = (body.centerx + self.facing * 14, body.centery - 4)
            tip = (body.centerx + self.facing * 78, body.centery - 22)
        else:
            hand = (body.centerx + self.facing * 8, body.centery + 10)
            tip = (body.centerx + self.facing * 22, body.top + 6)
        return hand, tip

    def _begin_attack(self, heavy=False) -> None:
        """Inicia o golpe: avanço curto, hitbox ainda não existe (espera a janela ativa)."""
        self.attacking = True
        self.attack_timer = PLAYER_ATTACK_FRAMES
        self.attack_cooldown = 20 if heavy else 14
        self.strike_spawned = False
        self.pending_strike = None
        self.rect.x += self.facing * 10
        self._heavy = heavy
        if not heavy:
            self.spear_attacks += 1
            if self.spear_attacks % SPEAR_ROAR_EVERY == 0:
                self.roar()

    def _try_spawn_strike(self) -> None:
        """Cria a hitbox da lança só nos frames ativos do golpe."""
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
        """Entrega a hitbox pendente à PlayingState (no máximo uma por golpe)."""
        strike = self.pending_strike
        self.pending_strike = None
        return strike

    def take_damage(self, amount: float, source_x: float | None = None) -> float:
        """Aplica dano, knockback e flash. Bloqueio reduz o valor; i-frames ignoram o hit."""
        if self.invuln > 0:
            return 0
        if self.blocking:
            amount *= BLOCK_DAMAGE_FACTOR
        self.health = max(0.0, self.health - amount)
        if source_x is not None:
            push = -KNOCKBACK if source_x >= self.hurtbox.centerx else KNOCKBACK
            self.rect.x += push
        if self.blocking:
            self.invuln = BLOCK_RECOVERY_FRAMES
            self.flash_timer = 6
            self.flash_color = (255, 230, 150)
        else:
            self.invuln = PLAYER_INVULN_FRAMES
            self.flash_timer = 12
            self.flash_color = (255, 48, 36)
            self._cancel_bow()
        return amount


class AttackHitbox(pygame.sprite.Sprite):
    """Retângulo invisível do golpe do jogador; some após poucos frames."""

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
    """Inimigo com vida, stun, knockback e perseguição horizontal."""

    def __init__(self, x, y, image_path, health, speed, damage):
        super().__init__(x, y, image_path)
        self.health = health
        self.max_health = health
        self.speed = speed
        self.damage = damage
        self.vel_y = 0
        self.on_ground = True
        self.stun = 0
        self.flash_timer = 0
        self.flash_color = (255, 255, 255)

    @property
    def hurtbox(self) -> pygame.Rect:
        w = min(120, max(56, int(self.rect.width * 0.42)))
        h = min(110, max(48, int(self.rect.height * 0.55)))
        return pygame.Rect(self.rect.centerx - w // 2, self.rect.bottom - h, w, h)

    def take_hit(self, damage: int, source_x: float) -> None:
        self.health -= damage
        self.stun = HITSTUN_FRAMES
        self.flash_timer = 10
        self.flash_color = (255, 240, 210)
        push = KNOCKBACK + 6 if source_x < self.hurtbox.centerx else -(KNOCKBACK + 6)
        self.rect.x += push

    @property
    def weak_hurtbox(self) -> pygame.Rect | None:
        """Ponto fraco opcional. None = só a hurtbox normal."""
        return None

    def on_projectile_approach(self, projectile) -> str:
        """Hook futuro (Curupira): 'hit', 'deflect' ou 'dodge'."""
        return "hit"

    def move_towards(self, target_pos):
        """Anda no eixo X em direção ao alvo, respeitando stun e gravidade."""
        self.rect, self.vel_y, self.on_ground = apply_gravity_and_platforms(self.rect, self.vel_y, self.on_ground)
        if self.stun > 0:
            self.stun -= 1
            return
        dx = target_pos[0] - self.hurtbox.centerx
        if abs(dx) > 70:
            self.rect.x += int(self.speed * (1 if dx > 0 else -1))
        self.rect, self.vel_y, self.on_ground = apply_gravity_and_platforms(self.rect, self.vel_y, self.on_ground)


class SpectralJaguar(BaseEnemy):
    """Onça da onda — perseguição em galope, garras e mordidas."""

    def __init__(self, x, y, kind: str = "espectral"):
        kind = kind if kind in ("normal", "pantera", "espectral") else "espectral"
        stats = {
            "normal": (120, ONCA_WALK_SPEED, 7),
            "pantera": (130, ONCA_WALK_SPEED + 0.8, 8),
            "espectral": (140, ONCA_WALK_SPEED, 9),
        }
        health, speed, damage = stats[kind]
        super().__init__(x, y, "assets/enemy_onca_spectral.png", health=health, speed=speed, damage=damage)
        self.kind = kind
        self.walk_speed = ONCA_WALK_SPEED
        self.run_speed = ONCA_RUN_SPEED
        self.run_distance = ONCA_RUN_DISTANCE
        self.attack_range = 130
        self.recover_cooldown = 28
        self.strike_frames = 26
        self.anim_run = 5
        self.anim_walk = 9
        self.bite_lunge = 18
        self.charge_lunge = 20
        self.claw_damage = 9
        self.bite_damage = 12
        self.speed = self.walk_speed
        self.frames = {}
        for name in ("idle", "claw", "bite"):
            raw = pygame.image.load(f"assets/onca/{name}.png").convert_alpha()
            self.frames[name] = _scale_onca_frame(raw)
        idle = self.frames["idle"]
        bite = self.frames["bite"]
        self.frames["run1"] = _pose_from_base(idle, 1.04, 0.96)
        self.frames["run2"] = _pose_from_base(bite, 0.92, 0.94)
        self.image = self.frames["idle"]
        self.rect = self.image.get_rect(midbottom=(x, y))
        self.facing = -1
        self.action = "idle"
        self.action_timer = 0
        self.cooldown = 20
        self.next_attack = "claw"
        self.pending_melee = None
        self.melee_spawned = False
        self.pending_damage = self.claw_damage
        self.anim_tick = 0
        self.run_frame = 0
        self.running = False

    @property
    def hurtbox(self) -> pygame.Rect:
        w, h = int(96 * ONCA_SCALE), int(78 * ONCA_SCALE)
        return pygame.Rect(self.rect.centerx - w // 2, self.rect.bottom - h, w, h)

    @property
    def weak_hurtbox(self) -> pygame.Rect | None:
        """Cabeça da onça — só a flecha usa o multiplicador."""
        hb = self.hurtbox
        w, h = 30, 22
        return pygame.Rect(hb.centerx - w // 2, hb.top - 6, w, h)

    def _set_pose(self, name: str) -> None:
        frame = self.frames.get(name, self.frames["idle"])
        if self.facing < 0:
            frame = pygame.transform.flip(frame, True, False)
        midbottom = self.rect.midbottom
        self.image = frame
        self.rect = self.image.get_rect(midbottom=midbottom)

    def pop_melee(self) -> pygame.Rect | None:
        """Entrega a hitbox do golpe para a PlayingState aplicar no jogador."""
        box = self.pending_melee
        self.pending_melee = None
        return box

    def update(self, player_pos):
        self.facing = -1 if player_pos[0] < self.hurtbox.centerx else 1
        dist = abs(player_pos[0] - self.hurtbox.centerx)

        # Durante um golpe: pose, hitbox na janela ativa e avanço na mordida
        if self.action_timer > 0:
            self.action_timer -= 1
            pose = "claw" if self.action == "claw" else "bite"
            self._set_pose(pose)
            if not self.melee_spawned and 6 <= self.action_timer <= 14:
                reach = 88 if self.action == "claw" else 72
                hx = self.hurtbox.right - 8 if self.facing > 0 else self.hurtbox.left - reach + 8
                hy = player_pos[1] - 24
                self.pending_melee = pygame.Rect(hx, hy, reach, 50)
                self.pending_damage = self.claw_damage if self.action == "claw" else self.bite_damage
                self.melee_spawned = True
                if self.action == "bite":
                    self.rect.x += self.facing * self.bite_lunge
            if self.action_timer <= 0:
                self.action = "idle"
                self.cooldown = self.recover_cooldown
            self.rect, self.vel_y, self.on_ground = apply_gravity_and_platforms(self.rect, self.vel_y, self.on_ground)
            return

        if self.cooldown > 0:
            self.cooldown -= 1

        # Perto o bastante: alterna garra e mordida
        if self.stun <= 0 and self.cooldown <= 0 and dist < self.attack_range:
            self.action = self.next_attack
            self.next_attack = "bite" if self.next_attack == "claw" else "claw"
            self.action_timer = self.strike_frames
            self.melee_spawned = False
            if self.running:
                self.rect.x += self.facing * self.charge_lunge
            self._set_pose("claw" if self.action == "claw" else "bite")
            self.rect, self.vel_y, self.on_ground = apply_gravity_and_platforms(self.rect, self.vel_y, self.on_ground)
            return

        # Longe: galope; médio: caminhada
        self.running = self.stun <= 0 and dist > self.run_distance
        approaching = self.stun <= 0 and dist > 70
        self.speed = self.run_speed if self.running else self.walk_speed
        self.move_towards(player_pos)

        if approaching:
            self.anim_tick += 1
            cadence = self.anim_run if self.running else self.anim_walk
            if self.anim_tick % cadence == 0:
                self.run_frame = 1 - self.run_frame
            self._set_pose("run1" if self.run_frame == 0 else "run2")
        else:
            self.run_frame = 0
            self._set_pose("idle")


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
        self.damage = 12
        self.life = 160
        self.owner = "enemy"
        self.friendly = False

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


class Arrow(pygame.sprite.Sprite):
    """Flecha do Yáguar: a mesma da pose, voo linear em dt, ponta como collider."""

    friendly = True
    can_be_intercepted = True

    def __init__(self, x: float, y: float, angle: float, speed: float, damage: int, owner: str = "player"):
        super().__init__()
        self.owner = owner
        self.fx = float(x)
        self.fy = float(y)
        self.prev_x = self.fx
        self.prev_y = self.fy
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.damage = int(damage)
        self.life = BOW_LIFETIME
        self.spent = False
        self.stuck = False
        self.stuck_life = BOW_STUCK_TIME
        self.world_hit = False
        self._base = _arrow_image()
        self.image = self._base
        self.rect = self.image.get_rect(center=(int(self.fx), int(self.fy)))
        self._orient()

    def flight_segment(self) -> tuple[tuple[float, float], tuple[float, float]]:
        return (self.prev_x, self.prev_y), (self.fx, self.fy)

    def tip_rect(self) -> pygame.Rect:
        speed = math.hypot(self.vx, self.vy) or 1.0
        nose = max(8.0, self._base.get_width() * 0.48)
        tx = self.fx + self.vx / speed * nose
        ty = self.fy + self.vy / speed * nose
        return pygame.Rect(int(tx) - 3, int(ty) - 3, 7, 7)

    def _orient(self) -> None:
        ang = -math.degrees(math.atan2(self.vy, self.vx))
        self.image = pygame.transform.rotate(self._base, ang)
        self.rect = self.image.get_rect(center=(int(self.fx), int(self.fy)))

    def _stick(self, duration: float | None = None) -> None:
        self.stuck = True
        self.spent = True
        self.vx = 0.0
        self.vy = 0.0
        self.stuck_life = BOW_STUCK_TIME if duration is None else duration

    def deflect(self, scale: float = 0.55) -> None:
        """Hook para o Curupira desviar o projétil no futuro."""
        self.vx *= -scale
        self.vy = -abs(self.vy) * 0.45
        self.owner = "deflected"
        self._orient()

    def _hit_world(self) -> bool:
        p0, p1 = self.flight_segment()
        tip = self.tip_rect()
        for plat in platform_rects():
            if plat.clipline(p0, p1) or plat.colliderect(tip):
                return True
        return False

    def try_hit_enemy(self, enemy) -> tuple[bool, bool]:
        """True se o segmento ou a ponta acertou. Segundo valor = ponto fraco."""
        if self.spent or self.stuck:
            return False, False
        p0, p1 = self.flight_segment()
        tip = self.tip_rect()
        weak = getattr(enemy, "weak_hurtbox", None)
        if weak is not None and (weak.clipline(p0, p1) or weak.colliderect(tip)):
            return True, True
        hb = enemy.hurtbox
        if hb.clipline(p0, p1) or hb.colliderect(tip):
            return True, False
        return False, False

    def resolve_hit(self, weak: bool = False) -> int:
        """Marca impacto único e devolve o dano (com multiplicador de ponto fraco)."""
        if self.spent:
            return 0
        dmg = self.damage
        if weak:
            dmg = int(round(dmg * BOW_WEAK_MULT))
        self._stick(0.28)
        return dmg

    def update(self, dt: float = 1.0 / FPS, *args):
        if isinstance(dt, pygame.sprite.Group):
            dt = 1.0 / FPS
        dt = max(1e-4, min(0.05, float(dt)))
        if self.stuck:
            self.stuck_life -= dt
            if self.stuck_life <= 0:
                self.kill()
            return
        self.prev_x, self.prev_y = self.fx, self.fy
        self.vy += BOW_GRAVITY * dt
        self.fx += self.vx * dt
        self.fy += self.vy * dt
        self.life -= dt
        self._orient()
        if self._hit_world():
            self._stick()
            self.world_hit = True
            return
        if (
            self.life <= 0
            or self.fx < -80
            or self.fx > _world_width + 80
            or self.fy < -80
            or self.fy > SCREEN_HEIGHT + 120
        ):
            self.kill()


class MapinguariBoss(BaseEnemy):
    """Chefe final: combo de dois braços de perto e arremesso de tronco de longe."""

    def __init__(self, x, y):
        super().__init__(x, y, "assets/boss_mapinguari.png", health=320, speed=1.3, damage=11)
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
        self.pending_damage = 11
        self.melee_spawned = False
        self.log_spawned = False
        self.aim = (x, y)
        audio.play_mapinguari_roar()

    @property
    def hurtbox(self) -> pygame.Rect:
        w, h = 110, 190
        return pygame.Rect(self.rect.centerx - w // 2, self.rect.bottom - h, w, h)

    def _set_pose(self, name: str) -> None:
        # O gancho direito reusa o frame de ataque, rotacionado para parecer o outro braço.
        frame = self.frames.get("attack" if name == "swipe_right" else name, self.frames["idle"])
        if name == "swipe_right":
            frame = pygame.transform.rotate(frame, -16 * self.facing)
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
        # Fases: abaixo de 200 HP acelera; abaixo de 100 fica mais agressivo.
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
                # Primeiro golpe do combo: garra esquerda na altura do peito
                self._set_pose("attack")
                if not self.melee_spawned and 8 <= self.action_timer <= 16:
                    reach = 110
                    hx = self.hurtbox.right if self.facing > 0 else self.hurtbox.left - reach
                    hy = self.aim[1] - 28
                    self.pending_melee = pygame.Rect(hx, hy, reach, 56)
                    self.pending_damage = 11
                    self.melee_spawned = True
            elif self.action == "swipe_right":
                # Segundo golpe: gancho da mão direita, mais alto, com avanço
                self._set_pose("swipe_right")
                if not self.melee_spawned and 6 <= self.action_timer <= 14:
                    reach = 96
                    hx = self.hurtbox.right - 8 if self.facing > 0 else self.hurtbox.left - reach + 8
                    hy = self.hurtbox.top + 18
                    self.pending_melee = pygame.Rect(hx, hy, reach, 80)
                    self.pending_damage = 13
                    self.melee_spawned = True
                    self.rect.x += self.facing * 18
            elif self.action == "throw":
                self._set_pose("throw")
                if not self.log_spawned and self.action_timer <= 10:
                    hx, hy = self._hand_throw_point()
                    self.pending_log = TreeTrunk(hx, hy, self.aim)
                    self.log_spawned = True
            if self.action_timer <= 0:
                # Encadeia esquerda → direita; depois volta ao idle com cooldown
                if self.action == "attack":
                    self.action = "swipe_right"
                    self.action_timer = 32
                    self.melee_spawned = False
                else:
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
                audio.play_mapinguari_roar()
            elif dist > 170:
                self.action = "throw"
                self.action_timer = 42
                self.log_spawned = False
                self.facing = -1 if player_pos[0] < self.hurtbox.centerx else 1
                audio.play_mapinguari_roar()

        if self.action == "idle":
            self._set_pose("idle")
            self.move_towards(player_pos)


class HerbItem(GameObject):
    """Erva medicinal no chão; coleta cura o jogador."""

    def __init__(self, x, y):
        super().__init__(x, y, "assets/herb.png")
