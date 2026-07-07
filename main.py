from panda3d.core import loadPrcFileData
loadPrcFileData("", "window-title Orbital Defense")
loadPrcFileData("", "win-size 1280 720")

from panda3d.core import TextNode
from direct.gui.OnscreenText import OnscreenText
from direct.gui.DirectGui import DirectButton, DirectFrame, DirectWaitBar, DirectSlider
from direct.gui import DirectGuiGlobals as DGG

from direct.showbase.ShowBase import ShowBase

from panda3d.core import CardMaker, Shader, Vec2
from direct.showbase.ShowBaseGlobal import globalClock

from math import atan2, degrees, sqrt, sin, cos, pi
import random
from panda3d.core import TransparencyAttrib

from direct.gui.OnscreenImage import OnscreenImage

ENEMY_TYPES = {
    1: {"img": "Resources/sprites/enemy1.png", "w" : 24, "h" : 20, "speed" : 0.36, "radius" : 0.05, "score" : 10}, 
    2: {"img": "Resources/sprites/enemy2.png", "w" : 48, "h" : 40, "speed" : 0.22, "radius" : 0.09, "score" : 30},
    3: {"img": "Resources/sprites/enemy3.png", "w" : 48, "h" : 32, "speed" : 0.28, "radius" : 0.08, "score" : 20},
}
TOTAL_ROUNDS = 5
ENEMIES_ROUND_1 = 4
ENEMIES_PER_ROUND = 2

def length(x, y):
    return sqrt(x * x + y * y )

class Sprite:
    def __init__(self, image, w_px, h_px, x, y, parent):
        self.node = OnscreenImage(image = image, parent = parent)
        self.node.setTransparency(TransparencyAttrib.MAlpha)
        self.node.setScale((w_px / 720) * 1.4, 1, (h_px / 720) * 1.4)
        self.x, self.y = x, y
        self.vx, self.vy = 0.0, 0.0
        self._apply()
    
    def _apply(self):
        self.node.setPos(self.x, 0, self.y)
    
    def move(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self._apply()
    
    def face(self, dx, dy):
        self.node.setR(90 - degrees(atan2(dy, dx)))

    def destroy(self):
        self.node.removeNode()

class Game(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        self.disableMouse()

        self.accept("mouse1", self.on_fire_down)
        self.accept("mouse1-up", self.on_fire_up)

        # ---- Audio: music + SFX, both default to 50% volume ----
        # Volumes are backed by these vars (source of truth) so the 50% default and
        # any slider change are remembered regardless of the audio backend.
        self.music_volume = 0.5
        self.sfx_volume = 0.5
        self.music = self.loader.loadMusic("Resources/audio/music.ogg")
        self.music.setLoop(True)
        self.musicManager.setVolume(self.music_volume)   # 50% music default
        self.music.play()                         # plays immediately, through menu + gameplay
        # A small pool of shoot SFX so rapid bursts overlap cleanly instead of cutting off.
        self.sfx_shoot_pool = [self.loader.loadSfx("Resources/audio/projectile.wav") for _ in range(4)]
        self.sfx_shoot_idx = 0
        self.sfx_impact = self.loader.loadSfx("Resources/audio/impact.wav")
        self.sfxManagerList[0].setVolume(self.sfx_volume)   # 50% SFX default

        self.aspect = self.getAspectRatio()
        self.state = "menu"
        self.menu_nodes = []
        self.pause_nodes = []
        self.suspended_game = False           # a paused game kept alive so Continue can resume it
        self.accept("escape", self.toggle_pause)
        self.accept("p", self.toggle_pause)
        self.build_starfield()
        self.show_menu()
        self.taskMgr.add(self.update, "update")
    
    def show_menu(self):
        self.state = "menu"
        if not self.suspended_game:        # keep a paused game alive so Continue can resume it
            self.clear_game()
        title = OnscreenText(text = "ORBITAL DEFENSE", pos = (0, 0.55), scale = 0.18, fg = (0.6, 0.9, 1, 1), align = TextNode.ACenter)
        self.menu_nodes.append(title)
        labels = [("New Game", self.start_game),
            ("Continue", self.continue_game),
            ("Settings", self.show_settings),
            ("Exit", self.userExit)]
        z = 0.2
        for text, cmd in labels:
            b = DirectButton(text = text,scale = 0.09, pos = (0, 0, z), frameColor = (0.1, 0.2, 0.35, 0.9), text_fg = (1, 1, 1, 1), relief = DGG.FLAT, pad = (0.5, 0.3), command = ( cmd if cmd else (lambda: None)) )
            self.menu_nodes.append(b)
            z -= 0.22

    def show_settings(self):
        # Settings screen. The starfield lives on render2d, so it already shows
        # behind this UI -- same flowing space background as the menu, for free.
        self.state = "settings"
        self.clear_menu()
        self.music_slider = None; self.music_pct = None
        self.sfx_slider = None;   self.sfx_pct = None

        title = OnscreenText(text = "SETTINGS", pos = (0, 0.6), scale = 0.16, fg = (0.6, 0.9, 1, 1), align = TextNode.ACenter)

        m_label = OnscreenText(text = "Game Music", pos = (-0.9, 0.24), scale = 0.07, fg = (0.6, 0.9, 1, 1), align = TextNode.ALeft)
        self.music_slider = DirectSlider(range = (0, 1), value = self.music_volume, pageSize = 0.05,
            pos = (0.3, 0, 0.26), scale = 0.5, command = self.set_music_volume,
            frameColor = (0.2, 0.3, 0.45, 1), thumb_frameColor = (0.6, 0.9, 1, 1), thumb_relief = DGG.FLAT)
        self.music_pct = OnscreenText(text = "", pos = (0.96, 0.24), scale = 0.07, fg = (1, 1, 1, 1), align = TextNode.ALeft, mayChange = True)

        s_label = OnscreenText(text = "Sound Effects", pos = (-0.9, 0.04), scale = 0.07, fg = (0.6, 0.9, 1, 1), align = TextNode.ALeft)
        self.sfx_slider = DirectSlider(range = (0, 1), value = self.sfx_volume, pageSize = 0.05,
            pos = (0.3, 0, 0.06), scale = 0.5, command = self.set_sfx_volume,
            frameColor = (0.2, 0.3, 0.45, 1), thumb_frameColor = (0.6, 0.9, 1, 1), thumb_relief = DGG.FLAT)
        self.sfx_pct = OnscreenText(text = "", pos = (0.96, 0.04), scale = 0.07, fg = (1, 1, 1, 1), align = TextNode.ALeft, mayChange = True)

        back = DirectButton(text = "Back", scale = 0.09, pos = (0, 0, -0.4), frameColor = (0.1, 0.2, 0.35, 0.9), text_fg = (1, 1, 1, 1), relief = DGG.FLAT, pad = (0.5, 0.3), command = self.show_menu)

        self.menu_nodes += [title, m_label, self.music_slider, self.music_pct, s_label, self.sfx_slider, self.sfx_pct, back]
        self.set_music_volume()
        self.set_sfx_volume()

    def set_music_volume(self):
        if getattr(self, "music_slider", None) is None:
            return
        v = self.music_slider["value"]
        self.music_volume = v
        self.musicManager.setVolume(v)               # adjusts MUSIC only
        if getattr(self, "music_pct", None) is not None:
            self.music_pct.setText("%d%%" % round(v * 100))

    def set_sfx_volume(self):
        if getattr(self, "sfx_slider", None) is None:
            return
        v = self.sfx_slider["value"]
        self.sfx_volume = v
        self.sfxManagerList[0].setVolume(v)          # adjusts SFX only
        if getattr(self, "sfx_pct", None) is not None:
            self.sfx_pct.setText("%d%%" % round(v * 100))

    def begin_round(self, n):
        self.round = n
        count = ENEMIES_ROUND_1 + (n - 1) * ENEMIES_PER_ROUND
        self.to_spawn = count
        self.enemies_remaining = count
        self.spawn_timer = 0.0
        self.refresh_hud()

    def clear_menu(self):
        for n in self.menu_nodes:
            n.destroy()
        self.menu_nodes = []

    def start_game(self):
        self.clear_menu()
        self.clear_pause()
        self.suspended_game = False
        for n in getattr(self, "end_nodes", []):
            n.destroy()
        self.end_nodes = []
        self.clear_game()
        self.state = "playing"
        self.player = Sprite("Resources/sprites/player.png", 48, 40, 0, 0, self.aspect2d)
        self.score = 0
        self.ammo = 30
        self.health = 100
        self.round = 1

        self.enemies = []
        self.particles = []
        self.pickups = []
        self.pickup_timer = 0.0
        self.full_timer = 0.0          # counts down once 3 pickups are out (oldest then expires)
        self.enemies_remaining = 0

        # ---- shield state ----
        self.shield_charges = 1        # starts at 1, stacks to 5
        self.shield_active = False
        self.shield_timer = 0.0
        self.accept("space", self.activate_shield)
        # translucent blue sphere shown on the ship while shielded (hidden by default)
        self.shield_sphere = OnscreenImage(image = "Resources/sprites/shield_sphere.png", parent = self.aspect2d)
        self.shield_sphere.setTransparency(TransparencyAttrib.MAlpha)
        self.shield_sphere.setScale(0.16)         # ~2x the ship
        self.shield_sphere.setBin("fixed", 10)
        self.shield_sphere.hide()

        self.player_shots = []
        self.trigger_held = False
        self.shots_since_press = 3
        self.fire_timer = 0.0
        self.enemy_shots = []
        self.hud = {}
        self.build_hud()
        self.to_spawn = 0
        self.begin_round(1)
    
    def spawn_enemy(self):
        spec = ENEMY_TYPES[random.choice([1, 2, 3])]
        ang = random.uniform(0, 2 * pi)
        x, y = cos(ang) * 2.2, sin(ang) * 2.2
        e = Sprite(spec["img"], spec["w"], spec["h"], x, y, self.aspect2d)
        e.speed, e.radius, e.score = spec["speed"], spec["radius"], spec["score"]
        e.fire_cd = random.uniform(0.3, 1.3)
        self.enemies.append(e)

    def spawn_pickup(self):
        kind = random.choice(["ammo", "hp", "shield"])
        x = random.uniform(-self.aspect + 0.2, self.aspect - 0.2)
        y = random.uniform(-0.8, 0.8)
        if kind == "ammo":
            p = Sprite("Resources/sprites/ammo.png", 16, 52, x, y, self.aspect2d)
        elif kind == "hp":
            p = Sprite("Resources/sprites/hp.png", 38, 38, x, y, self.aspect2d)
        else:
            p = Sprite("Resources/sprites/shield.png", 38, 38, x, y, self.aspect2d)
        p.kind = kind
        p.radius = 0.04
        p.spawn_time = globalClock.getFrameTime()
        self.pickups.append(p)

    def move_enemies(self, dt):
        for e in self.enemies:
            dx, dy = -e.x, -e.y
            d = length(dx, dy)
            if d > 0.0001:
                e.vx, e.vy = dx/ d * e.speed, dy / d * e.speed
            e.move(dt)
            e.face(dx, dy)
            if length(self.player.x - e.x, self.player.y - e.y) < 0.9:
                e.fire_cd -= dt
                if e.fire_cd <= 0:
                    self.enemy_fire(e)
                    e.fire_cd = 1.3

    def explode(self, x, y):
        for _ in range(12):
            cm = CardMaker("p")
            cm.setFrame(-0.012, 0.012, -0.012, 0.012)
            n = self.aspect2d.attachNewNode(cm.generate())
            n.setPos(x, 0, y)
            n.setColor(1, random.uniform(0.4, 0.8), 0.1, 1)
            n.setTransparency(TransparencyAttrib.MAlpha)
            ang, spd = random.uniform(0, 2 * pi), random.uniform(0.4, 1)
            self.particles.append({"node":n, "vx": cos(ang) * spd, "vy": sin(ang) * spd, "x": x, "y": y, "life": 0.5})
    
    def update_particles(self, dt):
        for p in self.particles[:]:
            p["life"] -= dt
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["node"].setPos(p["x"], 0, p["y"])
            p["node"].setAlphaScale(max(0.0, p["life"] / 0.5))
            if p["life"] <= 0:
                p["node"].removeNode()
                self.particles.remove(p)

    def destroy_enemy(self, e, give_score):
        self.explode(e.x, e.y)
        if give_score:
            self.score += e.score
        e.destroy()
        self.enemies.remove(e)
        self.enemies_remaining -= 1

    def enemy_fire(self, e):
        dx, dy = self.player.x - e.x, self.player.y - e.y
        d = length(dx, dy)
        if d < 0.0001:
            return
        dx, dy = dx/d , dy/d
        s = Sprite("Resources/sprites/enemyProjectile.png", 16, 52, e.x + dx * e.radius, e.y + dy * e.radius, self.aspect2d)
        s.vx, s.vy = dx * 1.4, dy * 1.4
        s.face(dx, dy)
        s.radius = 0.02
        self.enemy_shots.append(s)
    
    def build_hud(self):
        self.hud["health"] = DirectWaitBar(value = self.health, range = 100, parent = self.a2dTopCenter, pos = (0, 0, -0.1), scale = 0.5, barColor = (0.2, 0.9, 0.3, 1), frameColor = (0.1, 0.1, 0.1, 0.7))
        self.hud["shield"] = DirectWaitBar(value = self.shield_charges, range = 5, parent = self.a2dTopCenter, pos = (0, 0, -0.2), scale = 0.5, barColor = (0.3, 0.6, 1, 1), frameColor = (0.1, 0.1, 0.1, 0.7))
        self.hud["ammo"]  = OnscreenText(text = "", parent = self.a2dTopLeft, pos = (0.08, -0.12), scale = 0.07, fg = (1,1,1,1), align = TextNode.ALeft, mayChange = True)
        self.hud["score"]  = OnscreenText(text = "", parent = self.a2dTopRight, pos = (-0.5, -0.12), scale = 0.07, fg = (1,1,1,1), align = TextNode.ALeft, mayChange = True)
        self.hud["round"]  = OnscreenText(text = "", parent = self.a2dBottomLeft, pos = (0.08, 0.1), scale = 0.07, fg = (1,1,1,1), align = TextNode.ALeft, mayChange = True)
        self.hud["enemies"]  = OnscreenText(text = "", parent = self.a2dBottomRight, pos = (-1, 0.1), scale = 0.07, fg = (1,1,1,1), align = TextNode.ALeft, mayChange = True)
        self.refresh_hud()
    
    def refresh_hud(self):
        if not self.hud:
            return
        
        self.hud["health"]["value"] = self.health
        self.hud["shield"]["value"] = self.shield_charges
        self.hud["ammo"].setText("AMMO: %d" % self.ammo)
        self.hud["score"].setText("SCORE: %d" % self.score)
        self.hud["round"].setText("ROUND %d" % self.round)
        self.hud["enemies"].setText("ENEMIES REMAINING: %d" % self.enemies_remaining)

    def aim_dir(self):
        if self.mouseWatcherNode.hasMouse():
            mx = self.mouseWatcherNode.getMouseX() * self.aspect
            my = self.mouseWatcherNode.getMouseY()
            d = length(mx, my)
            if d > 0.0001:
                return mx / d, my / d
        return 0.0, 1.0

    def on_fire_down(self):
        if self.state != "playing":
            return 
        self.trigger_held = True
        self.shots_since_press = 0
        self.fire_timer = 0.0
    
    def on_fire_up(self):
        self.trigger_held = False

    def fire_one(self):
        dx, dy = self.aim_dir()
        s = Sprite("Resources/sprites/playerProjectile.png", 16, 52, self.player.x + dx * 0.07, self.player.y + dy * 0.07, self.aspect2d)
        s.vx, s.vy = dx * 2.2, dy * 2.2
        s.face(dx, dy)
        s.radius = 0.02
        self.player_shots.append(s)
        self.ammo -= 1
        # shoot SFX -- rotate through the pool so bursts don't cut each other off
        self.sfx_shoot_pool[self.sfx_shoot_idx].play()
        self.sfx_shoot_idx = (self.sfx_shoot_idx + 1) % len(self.sfx_shoot_pool)

    def activate_shield(self):
        # Spacebar: spend one charge for 1s of invincibility + the blue sphere.
        if self.state != "playing":
            return
        if self.shield_charges > 0 and not self.shield_active:
            self.shield_charges -= 1
            self.shield_active = True
            self.shield_timer = 1.0
            self.shield_sphere.setPos(self.player.x, 0, self.player.y)
            self.shield_sphere.show()
            self.refresh_hud()

    def build_starfield(self):
        cm = CardMaker("starfield")
        cm.setFrameFullscreenQuad()
        self.starfield = self.render2d.attachNewNode(cm.generate())
        self.starfield.setBin("background", 0)
        self.starfield.setDepthWrite(False)
        shader = Shader.load(Shader.SL_GLSL, vertex = "starfield.vert", fragment = "starfield.frag")
        self.starfield.setShader(shader)
        self.starfield.setShaderInput("u_resolution", Vec2(1280, 720))
        self.starfield.setShaderInput("u_time", 0.0)

    def clear_game(self):
        for name in ("enemies", "player_shots", "enemy_shots", "pickups"):
            for o in getattr(self, name, []):   
                o.destroy()
        for p in getattr(self, "particles", []):
            p["node"].removeNode()
        if getattr(self, "player", None):
            self.player.destroy()
        for n in getattr(self, "hud", {}).values():
            n.destroy()
        if getattr(self, "shield_sphere", None) is not None:
            self.shield_sphere.removeNode()
            self.shield_sphere = None
        self.shield_active = False
        self.enemies = []
        self.player_shots = []
        self.enemy_shots = []
        self.pickups = []
        self.particles = []
        self.hud = {}
        self.player = None

    # ---------------- Pause / Resume / Continue ----------------
    def toggle_pause(self):
        # Esc or P: pause while playing, resume while paused.
        if self.state == "playing":
            self.pause_game()
        elif self.state == "paused":
            self.resume_game()

    def pause_game(self):
        self.state = "paused"                    # update() freezes all game logic while paused
        frame = DirectFrame(frameColor = (0, 0, 0, 0.6), frameSize = (-2, 2, -1, 1))
        t = OnscreenText(text = "PAUSED", pos = (0, 0.35), scale = 0.2, fg = (0.6, 0.9, 1, 1), align = TextNode.ACenter, parent = self.aspect2d)
        hint = OnscreenText(text = "Esc / P to resume", pos = (0, 0.2), scale = 0.06, fg = (0.7, 0.8, 0.9, 1), align = TextNode.ACenter, parent = self.aspect2d)
        b_res = DirectButton(text = "Resume", scale = 0.09, pos = (0, 0, -0.05), frameColor = (0.1, 0.2, 0.35, 0.95), text_fg = (1, 1, 1, 1), relief = DGG.FLAT, pad = (0.5, 0.3), command = self.resume_game)
        b_menu = DirectButton(text = "Main Menu", scale = 0.09, pos = (0, 0, -0.27), frameColor = (0.1, 0.2, 0.35, 0.95), text_fg = (1, 1, 1, 1), relief = DGG.FLAT, pad = (0.5, 0.3), command = self.quit_to_menu)
        self.pause_nodes = [frame, t, hint, b_res, b_menu]

    def clear_pause(self):
        for n in getattr(self, "pause_nodes", []):
            n.destroy()
        self.pause_nodes = []

    def resume_game(self):
        self.clear_pause()
        self.state = "playing"

    def quit_to_menu(self):
        # Keep the run hidden (not destroyed) so Continue can bring it back.
        self.clear_pause()
        self.hide_game()
        self.suspended_game = True
        self.show_menu()

    def continue_game(self):
        if self.suspended_game and getattr(self, "player", None):
            self.clear_menu()
            self.show_game()
            self.suspended_game = False
            self.state = "playing"

    def _game_nodes(self):
        nodes = []
        for name in ("enemies", "player_shots", "enemy_shots", "pickups"):
            nodes += [o.node for o in getattr(self, name, [])]
        if getattr(self, "player", None):
            nodes.append(self.player.node)
        if getattr(self, "shield_sphere", None) is not None:
            nodes.append(self.shield_sphere)
        nodes += [p["node"] for p in getattr(self, "particles", [])]
        return nodes

    def hide_game(self):
        for n in self._game_nodes():
            n.hide()
        for n in getattr(self, "hud", {}).values():
            n.hide()

    def show_game(self):
        for n in self._game_nodes():
            n.show()
        for n in getattr(self, "hud", {}).values():
            n.show()
        if getattr(self, "shield_sphere", None) is not None and not self.shield_active:
            self.shield_sphere.hide()    # sphere only visible while the shield is active

    def show_end_screen(self, title_text, button_text, color):
        frame = DirectFrame(frameColor = (0, 0, 0, 0.6), frameSize = (-2, 2, -1, 1))
        t = OnscreenText(text = title_text, pos = (0, 0.25), scale = 0.2, fg = color, align = TextNode.ACenter, parent = self.aspect2d)
        b = DirectButton(text = button_text, scale = 0.1, pos = (0, 0, -0.15), frameColor = (0.1, 0.2, 0.35, 0.95), text_fg = (1, 1, 1, 1), relief = DGG.FLAT, pad = (0.5, 0.3), command = self.start_game)
        self.end_nodes = [frame, t, b]

    def lose(self):
        self.state = "lose"
        self.clear_game()
        self.show_end_screen("YOU LOSE", "Try Again", (1, 0.4, 0.4, 1))

    def win_game(self):
        self.state = "win"
        self.clear_game()
        self.show_end_screen("YOU WIN", "Play Again", (0.5, 1, 0.6, 1))
    
    def update(self, task):
        self.starfield.setShaderInput("u_time", globalClock.getFrameTime())
        dt = globalClock.getDt()
        if self.state == "playing":
            # Pickup cap: at most 3 at once. Spawn only when there is room, at the
            # existing random cadence. When the 3rd spawns, start a 10s timer; when
            # it elapses the oldest (front of the list) is removed to free a slot.
            self.pickup_timer -= dt
            if self.pickup_timer <= 0 and len(self.pickups) < 3:
                self.spawn_pickup()
                self.pickup_timer = random.uniform(3.0, 6.0)
                if len(self.pickups) == 3:
                    self.full_timer = 10.0
            if len(self.pickups) >= 3:
                self.full_timer -= dt
                if self.full_timer <= 0:
                    old = self.pickups.pop(0)
                    old.destroy()

            # shield countdown + keep the sphere on the ship while active
            if self.shield_active:
                self.shield_timer -= dt
                self.shield_sphere.setPos(self.player.x, 0, self.player.y)
                if self.shield_timer <= 0:
                    self.shield_active = False
                    self.shield_sphere.hide()

            dx, dy = self.aim_dir()
            self.player.face(dx, dy)
            BURST, INTERVAL = 3, 0.10
            want = self.trigger_held or self.shots_since_press < BURST
            self.fire_timer -= dt
            if want and self.fire_timer <= 0 and self.ammo > 0:
                self.fire_one()
                self.shots_since_press += 1
                self.fire_timer = INTERVAL

            if self.to_spawn > 0:
                self.spawn_timer -= dt
                if self.spawn_timer <= 0:
                    self.spawn_enemy()
                    self.to_spawn -= 1
                    self.spawn_timer = 0.8

            for s in self.player_shots[:]:
                s.move(dt)
                if abs(s.x) > self.aspect + 0.3 or abs(s.y) > 1.3:
                    s.destroy()
                    self.player_shots.remove(s)

            for s in self.player_shots[:]:
                hit = False
                for e in self.enemies[:]:
                    if length(s.x - e.x, s.y - e.y) < s.radius + e.radius:
                        self.destroy_enemy(e, give_score = True)
                        self.sfx_impact.play()          # impact SFX on enemy hit
                        hit = True
                        break
                if hit:
                    s.destroy()
                    self.player_shots.remove(s)
                    continue
                
                for p in self.pickups[:]:
                    if length(s.x - p.x, s.y - p.y) < s.radius + p.radius:
                        if p.kind == "ammo":
                            self.ammo += 10
                        elif p.kind == "hp":
                            self.health = min(100, self.health + 10)        # +10% of max HP
                        elif p.kind == "shield":
                            self.shield_charges = min(5, self.shield_charges + 1)
                        p.destroy()
                        self.pickups.remove(p)
                        s.destroy()
                        self.player_shots.remove(s)
                        self.refresh_hud()
                        break

            for s in self.enemy_shots[:]:
                s.move(dt)
                if abs(s.x) > self.aspect + 0.3 or abs(s.y) > 1.3:
                    s.destroy()
                    self.enemy_shots.remove(s)
                    continue
                if length(s.x - self.player.x, s.y - self.player.y) < s.radius + 0.07:
                    if not self.shield_active:                  # invincible while shielded
                        self.health -= 8
                    s.destroy()
                    self.enemy_shots.remove(s)
            for e in self.enemies[:]:
                    if length(e.x - self.player.x, e.y - self.player.y) < e.radius + 0.07:
                        if not self.shield_active:              # invincible while shielded
                            self.health -= 20
                        self.destroy_enemy(e, give_score = False)
                        break

            self.move_enemies(dt)
            self.update_particles(dt)
            self.refresh_hud()

            if self.health <= 0:
                self.lose()
            elif self.enemies_remaining <= 0 and self.to_spawn <= 0:
                if self.round >= TOTAL_ROUNDS:
                    self.win_game()
                else:
                    self.begin_round(self.round + 1)
        return task.cont

if __name__ == "__main__":
    Game().run()
    
