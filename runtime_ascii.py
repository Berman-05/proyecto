"""
runtime_ascii.py
Ventana visual 2D ASCII para ejecutar acciones del lenguaje RPG.

El modulo esta separado del analizador/interprete para que el compilador pueda
alimentar posiciones, controles y acciones sin mezclar logica de UI con parsing.
"""

from dataclasses import dataclass
import tkinter as tk
from tkinter import font


DEFAULT_KEYS = {
    "left": "Left",
    "right": "Right",
    "ability": "space",
}

CONTROL_GLOBALS = {
    "tecla_izquierda": "left",
    "tecla_derecha": "right",
    "tecla_habilidad": "ability",
}


@dataclass
class Entity:
    """Entidad renderizable dentro de la matriz ASCII."""

    name: str
    symbol: str
    x: int
    y: int
    direction: str = "right"
    executing_ability: bool = False
    hp: int = 100
    max_hp: int = 100
    xp: int = 0
    xp_reward: int = 0
    level: int = 1
    learned_abilities: set = None
    is_player: bool = False
    defeated: bool = False
    ai_walk_direction: int = -1
    ai_tick: int = 0
    attack_cooldown: int = 0
    ability_name: str = None
    template_name: str = None


@dataclass
class Ability:
    name: str
    damage: int = 0
    kind: str = "melee"
    distance: int = 3
    level_required: int = 1


class AsciiSideScrollerRuntime:
    """
    Administra una ventana Tkinter con una matriz ASCII lateral.

    Flujo de integracion:
      1. Crear la instancia.
      2. Llamar set_player(...) y add_enemy(...) o cargar desde tabla_simbolos.
      3. El interprete puede llamar walk("player", pasos) o use_ability(...).
      4. start() activa el loop con after() a ~30 FPS.
    """

    def __init__(
        self,
        master=None,
        width=80,
        height=22,
        fps=30,
        key_bindings=None,
        title="RPG ASCII Runtime",
    ):
        self.master = master
        self.root = tk.Toplevel(master) if master is not None else tk.Tk()
        self.root.title(title)
        self.root.configure(bg="#071019")

        self.width = width
        self.height = height
        self.floor_y = height - 3
        self.fps = fps
        self.frame_ms = max(1, int(1000 / fps))
        self.key_bindings = dict(DEFAULT_KEYS)
        if key_bindings:
            self.key_bindings.update(key_bindings)

        self.player = None
        self.enemies = []
        self.enemy_templates = {}
        self.waves = []
        self.current_wave_index = -1
        self.pressed_keys = set()
        self.running = False
        self._after_id = None
        self._ability_frames = 0
        self._message_frames = 0
        self._message = "Listo"
        self.game_state = "PLAYING"
        self.ability_damage = {}
        self.abilities = {}
        self.ability_keys = {}
        self.default_player_ability = "ataque"
        self.player_attack_damage = 10
        self.enemy_attack_damage = 5
        self.enemy_default_ability = None
        self.attack_pattern = "*-~"
        self.contact_range = 1
        self.game_over = False
        self.player_start = (4, self.floor_y - 1)
        self._wave_after_id = None
        self._visual_source = None
        self._visual_ability_name = None

        mono = font.Font(family="Courier New", size=12)
        self.text = tk.Text(
            self.root,
            width=self.width,
            height=self.height,
            font=mono,
            bg="#071019",
            fg="#d7fbe8",
            insertbackground="#d7fbe8",
            relief="flat",
            padx=10,
            pady=10,
            state="disabled",
            wrap="none",
        )
        self.text.pack(fill="both", expand=True, padx=12, pady=(12, 6))

        self.status = tk.Label(
            self.root,
            text="",
            bg="#071019",
            fg="#8fb3a5",
            anchor="w",
            font=("Segoe UI", 9),
        )
        self.status.pack(fill="x", padx=12, pady=(0, 12))

        self.root.bind("<KeyPress>", self._on_key_press)
        self.root.bind("<KeyRelease>", self._on_key_release)
        self.root.bind("<KeyPress-r>", lambda event: self.reset_game())
        self.root.bind("<KeyPress-R>", lambda event: self.reset_game())
        self.root.protocol("WM_DELETE_WINDOW", self.stop)
        self.root.focus_force()

    # ------------------------------------------------------------------
    # Construccion desde el compilador/interprete
    # ------------------------------------------------------------------
    @classmethod
    def from_symbol_table(cls, tabla_simbolos, tokens_raw=None, master=None):
        """Crea una escena usando los personajes y acciones del analisis semantico."""
        key_bindings = cls.extract_key_bindings(tabla_simbolos)
        runtime = cls(master=master, key_bindings=key_bindings)
        runtime.feed_abilities(tabla_simbolos)
        runtime.feed_ability_key_bindings(tabla_simbolos)
        runtime.feed_symbol_table(tabla_simbolos)
        runtime.feed_waves(tabla_simbolos)
        runtime.feed_enemy_actions(tabla_simbolos)
        return runtime

    @staticmethod
    def extract_key_bindings(tabla_simbolos):
        """
        Permite definir controles en el codigo del compilador con variables globales:

            tecla_izquierda = "a";
            tecla_derecha = "d";
            tecla_habilidad = "j";

        Tkinter usa nombres como Left, Right, space, a, d, j, etc.
        """
        keys = {}
        for variable_name, action_name in CONTROL_GLOBALS.items():
            entry = tabla_simbolos.get(variable_name)
            if not entry or entry.get("categoria") != "variable_global":
                continue
            slot = entry.get("valor", {}).get("_val", {})
            value = slot.get("valor")
            if isinstance(value, str) and value:
                keys[action_name] = "space" if value.lower() == "espacio" else value
        return keys

    def feed_abilities(self, tabla_simbolos):
        """Carga el dano de cada habilidad declarada para el combate visual."""
        for name, data in tabla_simbolos.items():
            if data.get("categoria") != "habilidad":
                continue
            values = data.get("valor", {})
            damage = values.get("dano", {}).get("valor", 0)
            kind = values.get("tipo", {}).get("valor", "melee")
            distance = values.get("distancia", {}).get("valor")
            level_required = values.get("nivel", {}).get("valor", 1)

            if kind in ("rango", "distancia"):
                kind = "ranged"
            elif kind not in ("melee", "ranged"):
                kind = "melee"

            if distance is None:
                distance = 6 if kind == "ranged" else len(self.attack_pattern)

            self.abilities[name] = Ability(
                name=name,
                damage=int(damage),
                kind=kind,
                distance=max(1, int(distance)),
                level_required=max(1, int(level_required or 1)),
            )
            self.ability_damage[name] = int(damage)
            if self.default_player_ability == "ataque":
                self.default_player_ability = name
                self.player_attack_damage = int(damage)

        enemy_damage_slot = tabla_simbolos.get("dano_enemigo", {}).get("valor", {}).get("_val", {})
        enemy_damage = enemy_damage_slot.get("valor")
        if isinstance(enemy_damage, int):
            self.enemy_attack_damage = max(1, enemy_damage)

    def feed_ability_key_bindings(self, tabla_simbolos):
        """
        Permite mapear habilidades a teclas desde el codigo:

            tecla_Golpe = "j";
            tecla_Flecha = "k";
        """
        self.ability_keys = {}
        for variable_name, entry in tabla_simbolos.items():
            if not variable_name.startswith("tecla_"):
                continue
            if variable_name in CONTROL_GLOBALS:
                continue
            ability_name = variable_name[len("tecla_"):]
            if ability_name not in self.abilities:
                continue
            slot = entry.get("valor", {}).get("_val", {})
            value = slot.get("valor")
            if isinstance(value, str) and value:
                self.ability_keys[ability_name] = "space" if value.lower() == "espacio" else value

    def feed_symbol_table(self, tabla_simbolos):
        """
        Convierte personajes semanticos en entidades de la matriz.

        Regla simple:
          - El primer personaje declarado es Player y se renderiza con '@'.
          - Los siguientes personajes son enemigos NPC y se renderizan con 'E'.

        Si luego agregas una propiedad semantica explicita como rol="npc", este
        metodo es el punto donde mapearla sin tocar el motor visual.
        """
        personajes = [
            (nombre, datos)
            for nombre, datos in tabla_simbolos.items()
            if datos.get("categoria") == "personaje"
        ]

        if not personajes:
            self.set_player("Jugador", x=4)
            return

        for index, (nombre, datos) in enumerate(personajes):
            # El runtime parte del HP base y aplica las acciones visualmente.
            # HP_actual queda para la salida textual del analizador semantico.
            hp = datos.get("valor", {}).get("HP", {}).get("valor", 100)
            xp = datos.get("valor", {}).get("XP", {}).get("valor", 0)
            level = datos.get("apariencia", {}).get("nivel", {}).get("valor", 1)

            if index == 0:
                self.set_player(nombre, x=4, hp=hp, xp=xp, level=level)
            else:
                self.enemy_templates[nombre] = {
                    "name": nombre,
                    "hp": hp,
                    "xp_reward": xp,
                    "level": level,
                    "ability_name": None,
                }

        if self.player:
            self.player_start = (self.player.x, self.player.y)

    def feed_waves(self, tabla_simbolos):
        """Carga oleadas definidas en codigo y activa la primera."""
        self.waves = []
        for name, data in tabla_simbolos.items():
            if data.get("categoria") != "oleada":
                continue
            enemies = data.get("valor", {}).get("enemigo", {}).get("valor", [])
            if enemies:
                self.waves.append({"name": name, "enemies": list(enemies)})

        if not self.waves and self.enemy_templates:
            self.waves.append({
                "name": "Oleada1",
                "enemies": list(self.enemy_templates.keys()),
            })

        self.current_wave_index = -1
        self.spawn_next_wave()

    def feed_enemy_actions(self, tabla_simbolos):
        """
        Usa acciones del codigo como comportamiento inicial de NPC.

        Ejemplo de script:
            accion patrullaSlime {
                objetivo = Slime;
                caminar = 6;
            }

        Si objetivo apunta a un enemigo y caminar existe, ese enemigo obtiene una
        direccion inicial de patrulla. Las acciones con usar+objetivo se reflejan
        con use_ability(...) desde el interprete o en el arranque visual.
        """
        for action_name, data in tabla_simbolos.items():
            if data.get("categoria") != "accion":
                continue
            values = data.get("valor", {})
            target = values.get("objetivo", {}).get("valor")
            source_enemy = values.get("enemigo", {}).get("valor")
            steps = values.get("caminar", {}).get("valor")
            ability = values.get("usar", {}).get("valor")
            enemy = self.get_enemy(target)

            if enemy and steps is not None:
                enemy.ai_walk_direction = -1 if int(steps) < 0 else 1
                enemy.ai_tick = abs(int(steps))

            if source_enemy and ability in self.ability_damage:
                template = self.enemy_templates.get(source_enemy)
                if template is not None:
                    template["ability_name"] = ability
                for enemy_obj in self.enemies:
                    if enemy_obj.name == source_enemy or enemy_obj.template_name == source_enemy:
                        enemy_obj.ability_name = ability
                continue

            if self.player and target == self.player.name and ability in self.ability_damage:
                self.enemy_default_ability = ability
                self.enemy_attack_damage = self.ability_damage[ability]

    # ------------------------------------------------------------------
    # API publica para el interprete
    # ------------------------------------------------------------------
    def set_player(self, name, x=4, y=None, hp=100, xp=0, level=1):
        """Define o reemplaza al jugador principal."""
        self.player = Entity(
            name=name,
            symbol="@",
            x=self._clamp_x(x),
            y=self.floor_y - 1 if y is None else self._clamp_y(y),
            hp=hp,
            max_hp=hp,
            xp=xp,
            level=max(1, int(level or 1)),
            learned_abilities=set(),
            is_player=True,
        )
        return self.player

    def add_enemy(self, name, x=30, y=None, hp=100, xp_reward=0):
        """Agrega un NPC enemigo a la escena."""
        enemy = Entity(
            name=name,
            symbol="E",
            x=self._clamp_x(x),
            y=self.floor_y - 1 if y is None else self._clamp_y(y),
            hp=hp,
            max_hp=hp,
            xp_reward=xp_reward,
            is_player=False,
        )
        self.enemies.append(enemy)
        return enemy

    def inject_enemy(self, template_name, x=None):
        """API externa para que el compilador/runtime agregue enemigos sin romper el loop."""
        template = self.enemy_templates.get(template_name)
        if not template:
            return None
        x = self._clamp_x(x if x is not None else self.width - 8)
        enemy = self.add_enemy(
            template["name"],
            x=x,
            hp=template["hp"],
            xp_reward=template["xp_reward"],
        )
        enemy.template_name = template_name
        enemy.ability_name = template.get("ability_name") or self.enemy_default_ability
        return enemy

    def spawn_next_wave(self):
        """Elimina enemigos actuales, instancia la siguiente oleada y vuelve a PLAYING."""
        if self._wave_after_id is not None:
            try:
                self.root.after_cancel(self._wave_after_id)
            except tk.TclError:
                pass
            self._wave_after_id = None

        self.current_wave_index += 1
        if self.current_wave_index >= len(self.waves):
            self.current_wave_index = 0

        self.enemies = []
        wave = self.waves[self.current_wave_index] if self.waves else {"name": "Oleada", "enemies": []}
        for index, template_name in enumerate(wave["enemies"]):
            x = min(self.width - 6, 18 + index * 12)
            self.inject_enemy(template_name, x=x)

        self.game_state = "PLAYING"
        self.game_over = False
        self._message = f"{wave['name']} iniciada"
        self._message_frames = self.fps

    def reset_game(self):
        """Reinicia HP, posicion, enemigos de la oleada actual y vuelve a PLAYING."""
        if not self.player:
            return
        self.player.hp = self.player.max_hp
        self.player.x, self.player.y = self.player_start
        self.player.defeated = False
        self.player.symbol = "@"
        self.pressed_keys.clear()
        self.game_state = "PLAYING"
        self.game_over = False

        self.current_wave_index = max(-1, self.current_wave_index - 1)
        self.spawn_next_wave()

    def walk(self, entity_name="player", steps=1):
        """Mueve una entidad horizontalmente, como respuesta a accion caminar."""
        entity = self._resolve_entity(entity_name)
        if not entity or entity.defeated:
            return
        steps = int(steps)
        entity.direction = "right" if steps >= 0 else "left"
        entity.x = self._clamp_x(entity.x + steps)
        self._message = f"{entity.name} camina {abs(steps)} paso(s)"
        self._message_frames = self.fps

    def use_ability(self, source_name="player", target_name=None, ability_name="habilidad"):
        """Aplica dano real, activa el efecto visual y entrega XP si derrota."""
        if self.game_state != "PLAYING":
            return

        source = self._resolve_entity(source_name) or self.player
        if not source or source.defeated:
            return

        ability = self._ability_for(ability_name, enemy=source is not self.player)
        if source is self.player and self.player.level < ability.level_required:
            self._message = f"{ability_name} requiere nivel {ability.level_required}"
            self._message_frames = self.fps
            return

        if source is self.player:
            target = self._resolve_entity(target_name) if target_name else self._enemy_in_player_attack(ability_name)
        else:
            target = self._resolve_entity(target_name) if target_name else self.player

        if source is self.player and target is self.player and self.enemies:
            target = self._enemy_in_player_attack(ability_name)

        if not target:
            if source is self.player:
                self._show_ability_miss(source, ability_name, f"{ability_name} no conecta: sin objetivo en alcance")
            return

        if target.defeated:
            return

        if source is self.player and not self._player_attack_hits(target, ability):
            self._show_ability_miss(
                source,
                ability_name,
                f"{ability_name} no conecta: {target.name} esta fuera de alcance",
            )
            return

        if source:
            source.executing_ability = True
        if target:
            target.executing_ability = True
        self._visual_source = source
        self._visual_ability_name = ability_name

        damage = self._damage_for(source, ability_name)
        before_hp = target.hp
        target.hp = max(0, target.hp - damage)
        defeated_now = target.hp == 0 and before_hp > 0

        if defeated_now:
            target.defeated = True
            target.symbol = "x"
            if source is self.player:
                self._grant_defeat_rewards(target, ability_name)
                self._check_wave_clear()
            else:
                self._message = f"{source.name} derrota a {target.name}"
                self._message_frames = self.fps * 2
        elif source is self.player and ability_name not in ("input", "ataque"):
            self._learn_ability(ability_name)

        self._ability_frames = max(self._ability_frames, int(self.fps * 0.35))
        if not defeated_now:
            self._message = (
                f"{source.name} usa {ability_name}: -{damage} HP a {target.name} "
                f"({target.hp}/{target.max_hp})"
            )
            self._message_frames = self.fps

    def start(self):
        """Inicia el loop visual con Tkinter.after()."""
        if self.running:
            return
        self.running = True
        self.root.focus_force()
        self._loop()

    def stop(self):
        """Detiene el loop y cierra la ventana visual."""
        self.running = False
        if self._after_id is not None:
            try:
                self.root.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None
        if self._wave_after_id is not None:
            try:
                self.root.after_cancel(self._wave_after_id)
            except tk.TclError:
                pass
            self._wave_after_id = None
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    # ------------------------------------------------------------------
    # Loop e input
    # ------------------------------------------------------------------
    def _loop(self):
        if not self.running:
            return
        self._update()
        self._render()
        self._after_id = self.root.after(self.frame_ms, self._loop)

    def _update(self):
        if self.game_state != "PLAYING":
            self.pressed_keys.clear()
            if self._message_frames > 0:
                self._message_frames -= 1
            return

        player_used_ability = False
        if self.player:
            if self.key_bindings["left"] in self.pressed_keys:
                self.player.direction = "left"
                self.player.x = self._clamp_x(self.player.x - 1)
            if self.key_bindings["right"] in self.pressed_keys:
                self.player.direction = "right"
                self.player.x = self._clamp_x(self.player.x + 1)
            if self._ability_frames == 0:
                used_ability = self._pressed_player_ability()
                if used_ability:
                    self.use_ability("player", ability_name=used_ability)
                    player_used_ability = True

        if not player_used_ability:
            for enemy in self.enemies:
                self._update_enemy(enemy)

        if self._ability_frames > 0:
            self._ability_frames -= 1
            if self._ability_frames == 0:
                for entity in self._all_entities():
                    entity.executing_ability = False
                self._visual_source = None
                self._visual_ability_name = None

        if self._message_frames > 0:
            self._message_frames -= 1

    def _update_enemy(self, enemy):
        """IA simple: patrulla horizontalmente sobre el piso."""
        if enemy.defeated:
            return

        enemy.ai_tick += 1
        if enemy.attack_cooldown > 0:
            enemy.attack_cooldown -= 1

        if self.player and not self.player.defeated and self._enemy_can_hit_player(enemy):
            if enemy.attack_cooldown == 0:
                self._enemy_attack_player(enemy)
                enemy.attack_cooldown = self.fps
            return

        if enemy.ai_tick % 8 != 0:
            return

        next_x = enemy.x + enemy.ai_walk_direction
        if next_x <= 2 or next_x >= self.width - 3:
            enemy.ai_walk_direction *= -1
            next_x = enemy.x + enemy.ai_walk_direction
        enemy.direction = "right" if enemy.ai_walk_direction > 0 else "left"
        enemy.x = self._clamp_x(next_x)

    def _pressed_player_ability(self):
        for ability_name, key_name in self.ability_keys.items():
            if self._is_key_pressed(key_name):
                return ability_name
        if self._is_key_pressed(self.key_bindings["ability"]):
            return self.default_player_ability
        return None

    def _show_ability_miss(self, source, ability_name, message):
        source.executing_ability = True
        self._visual_source = source
        self._visual_ability_name = ability_name
        self._ability_frames = max(self._ability_frames, int(self.fps * 0.25))
        self._message = message
        self._message_frames = self.fps

    def _enemy_attack_player(self, enemy):
        if not self.player:
            return
        before_hp = self.player.hp
        ability_name = enemy.ability_name or self.enemy_default_ability or "ataque"
        damage = self._damage_for(enemy, ability_name)
        self.player.hp = max(0, self.player.hp - damage)
        enemy.executing_ability = True
        self.player.executing_ability = True
        self._visual_source = enemy
        self._visual_ability_name = ability_name
        self._ability_frames = max(self._ability_frames, int(self.fps * 0.25))

        if self.player.hp == 0 and before_hp > 0:
            self.player.defeated = True
            self.player.symbol = "X"
            self.game_over = True
            self.game_state = "GAME_OVER"
            self._message = f"GAME OVER - {enemy.name} derrota a {self.player.name}"
            self._message_frames = self.fps * 3
        else:
            self._message = (
                f"{enemy.name} golpea a {self.player.name}: "
                f"-{damage} HP ({self.player.hp}/{self.player.max_hp})"
            )
        self._message_frames = self.fps

    def _on_key_press(self, event):
        for key in self._event_key_names(event):
            self.pressed_keys.add(key)

    def _on_key_release(self, event):
        for key in self._event_key_names(event):
            self.pressed_keys.discard(key)

    @staticmethod
    def _event_key_names(event):
        keys = {event.keysym}
        if event.keysym:
            keys.add(event.keysym.lower())
            keys.add(event.keysym.upper())
        char = getattr(event, "char", "")
        if char:
            keys.add(char)
            keys.add(char.lower())
            keys.add(char.upper())
        return keys

    def _is_key_pressed(self, key_name):
        if not key_name:
            return False
        return (
            key_name in self.pressed_keys
            or key_name.lower() in self.pressed_keys
            or key_name.upper() in self.pressed_keys
        )

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------
    def _render(self):
        grid = self._empty_grid()

        # Fondo lateral: cielo simple, piso en capas y plataforma inferior.
        for x in range(self.width):
            grid[self.floor_y][x] = "="
            grid[self.floor_y + 1][x] = "#"
            grid[self.floor_y + 2][x] = "#"

        # Alimentar entidades al grid: x/y son coordenadas de columna/fila.
        for entity in self._all_entities():
            self._plot_entity(grid, entity)

        if self._ability_frames > 0:
            self._plot_ability(grid)

        if self.game_state == "GAME_OVER":
            self._plot_center_overlay(grid, "[ GAME OVER - Press 'R' to Restart ]")
        elif self.game_state == "VICTORY":
            self._plot_center_overlay(grid, "[ WAVE CLEAR - Next wave incoming ]")

        status_line = self._build_status_line()
        if self.height > 1:
            self._write_text(grid, 1, 1, status_line[: self.width - 2])

        output = "\n".join("".join(row) for row in grid)
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", output)
        self.text.configure(state="disabled")

        ability_controls = " ".join(
            f"{name}={key}" for name, key in sorted(self.ability_keys.items())
        ) or f"{self.default_player_ability}={self.key_bindings['ability']}"
        controls = (
            f"Controles: izquierda={self.key_bindings['left']}  "
            f"derecha={self.key_bindings['right']}  "
            f"{ability_controls}  reiniciar=R  estado={self.game_state}"
        )
        self.status.config(text=controls)

    def _empty_grid(self):
        return [[" " for _ in range(self.width)] for _ in range(self.height)]

    def _plot_entity(self, grid, entity):
        if not (0 <= entity.y < self.height and 0 <= entity.x < self.width):
            return

        grid[entity.y][entity.x] = entity.symbol
        if entity.defeated:
            if entity.y - 1 >= 0:
                self._write_text(grid, entity.y - 1, max(0, entity.x - 3), "KO")
            return

        marker = ">" if entity.direction == "right" else "<"
        marker_x = entity.x + (1 if entity.direction == "right" else -1)
        if 0 <= marker_x < self.width:
            grid[entity.y][marker_x] = marker

        name = entity.name[:10]
        name_x = max(0, min(self.width - len(name), entity.x - len(name) // 2))
        if entity.y - 1 >= 0:
            self._write_text(grid, entity.y - 1, name_x, name)

        hp_text = f"{max(entity.hp, 0)}/{entity.max_hp}hp"
        hp_x = max(0, min(self.width - len(hp_text), entity.x - len(hp_text) // 2))
        if entity.y + 1 < self.floor_y:
            self._write_text(grid, entity.y + 1, hp_x, hp_text)

    def _plot_ability(self, grid):
        source = self._visual_source or self.player
        if not source:
            return
        ability = self._ability_for(
            self._visual_ability_name or self.default_player_ability,
            enemy=source is not self.player,
        )
        for x, char in self._attack_cells(source, ability):
            if 0 <= x < self.width and 0 <= source.y < self.height:
                grid[source.y][x] = char

    def _build_status_line(self):
        if self.game_state == "GAME_OVER":
            return "GAME OVER - Press R to Restart"
        if self.game_state == "VICTORY":
            return "VICTORY - preparando siguiente oleada"
        if self._message_frames > 0:
            return self._message
        if not self.player:
            return "Sin jugador"
        abilities = ",".join(sorted(self.player.learned_abilities or [])) or "-"
        return (
            f"{self.player.name} HP={self.player.hp}/{self.player.max_hp} "
            f"LV={self.player.level} XP={self.player.xp}/{self._xp_to_next_level()} "
            f"HAB={abilities}"
        )

    @staticmethod
    def _write_text(grid, y, x, text):
        if y < 0 or y >= len(grid):
            return
        width = len(grid[y])
        for i, char in enumerate(text):
            col = x + i
            if 0 <= col < width:
                grid[y][col] = char

    # ------------------------------------------------------------------
    # Busqueda y limites
    # ------------------------------------------------------------------
    def _all_entities(self):
        entities = []
        if self.player:
            entities.append(self.player)
        entities.extend(self.enemies)
        return entities

    def _resolve_entity(self, name):
        if name in (None, "player", "jugador"):
            return self.player
        if self.player and self.player.name == name:
            return self.player
        return self.get_enemy(name)

    def get_enemy(self, name):
        for enemy in self.enemies:
            if enemy.name == name:
                return enemy
        return None

    def _nearest_enemy(self):
        if not self.player or not self.enemies:
            return None
        alive_enemies = [enemy for enemy in self.enemies if not enemy.defeated]
        if not alive_enemies:
            return None
        return min(alive_enemies, key=lambda enemy: abs(enemy.x - self.player.x))

    def _enemy_in_player_attack(self, ability_name=None):
        if not self.player:
            return None
        ability = self._ability_for(ability_name or self.default_player_ability)
        attack_xs = {x for x, _ in self._player_attack_cells(ability)}
        candidates = [
            enemy for enemy in self.enemies
            if not enemy.defeated and enemy.y == self.player.y and enemy.x in attack_xs
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda enemy: abs(enemy.x - self.player.x))

    def _damage_for(self, source, ability_name):
        if source is self.player:
            return self._ability_for(ability_name).damage
        return self._ability_for(ability_name, enemy=True).damage

    def _ability_for(self, ability_name, enemy=False):
        ability = self.abilities.get(ability_name)
        if ability:
            return ability
        return Ability(
            name=ability_name or "ataque",
            damage=self.enemy_attack_damage if enemy else self.player_attack_damage,
            kind="melee",
            distance=len(self.attack_pattern),
            level_required=1,
        )

    def _in_contact(self, a, b):
        return abs(a.x - b.x) <= self.contact_range and a.y == b.y

    def _enemy_can_hit_player(self, enemy):
        if not self.player or enemy.y != self.player.y:
            return False
        enemy.direction = "left" if self.player.x < enemy.x else "right"
        ability = self._ability_for(enemy.ability_name or self.enemy_default_ability, enemy=True)
        if ability.kind == "ranged":
            return self.player.x in {x for x, _ in self._attack_cells(enemy, ability)}
        return self._in_contact(enemy, self.player)

    def _player_attack_cells(self, ability=None):
        if not self.player:
            return []
        return self._attack_cells(self.player, ability)

    def _attack_cells(self, source, ability=None):
        if not source:
            return []
        ability = ability or self._ability_for(self.default_player_ability)
        direction = 1 if source.direction == "right" else -1
        if ability.kind == "ranged":
            chars = ("-", ">") if direction == 1 else ("<", "-")
            return [
                (source.x + direction * offset, chars[(offset - 1) % 2])
                for offset in range(1, ability.distance + 1)
            ]
        return [
            (
                source.x + direction * offset,
                self.attack_pattern[(offset - 1) % len(self.attack_pattern)],
            )
            for offset in range(1, ability.distance + 1)
        ]

    def _player_attack_hits(self, target, ability=None):
        if not self.player or not target:
            return False
        if target.y != self.player.y:
            return False
        return target.x in {x for x, _ in self._player_attack_cells(ability)}

    def _plot_center_overlay(self, grid, text):
        banner = text
        detail = f"Estado: {self.game_state}"
        y = max(2, self.height // 2 - 1)
        x = max(0, (self.width - len(banner)) // 2)
        detail_x = max(0, (self.width - len(detail)) // 2)
        self._write_text(grid, y, x, banner)
        self._write_text(grid, y + 1, detail_x, detail)

    def _grant_defeat_rewards(self, enemy, ability_name):
        if not self.player:
            return
        gained_xp = max(0, int(enemy.xp_reward or 0))
        self.player.xp += gained_xp
        learned = self._learn_ability(ability_name)
        leveled = self._apply_level_ups()

        details = [f"{enemy.name} derrotado", f"+{gained_xp} XP"]
        if learned:
            details.append(f"habilidad aprendida: {ability_name}")
        if leveled:
            details.append(f"nivel {self.player.level}")
        self._message = " | ".join(details)
        self._message_frames = self.fps * 2

    def _check_wave_clear(self):
        self.enemies = [enemy for enemy in self.enemies if not enemy.defeated]
        if self.enemies:
            return
        self.game_state = "VICTORY"
        self._message = "Oleada completada"
        self._message_frames = self.fps * 2
        self._wave_after_id = self.root.after(2000, self.spawn_next_wave)

    def _learn_ability(self, ability_name):
        if not self.player or not ability_name or ability_name == "input":
            return False
        if self.player.learned_abilities is None:
            self.player.learned_abilities = set()
        if ability_name in self.player.learned_abilities:
            return False
        self.player.learned_abilities.add(ability_name)
        return True

    def _apply_level_ups(self):
        leveled = False
        while self.player and self.player.xp >= self._xp_to_next_level():
            self.player.xp -= self._xp_to_next_level()
            self.player.level += 1
            self.player.max_hp += 10
            self.player.hp = self.player.max_hp
            leveled = True
        return leveled

    def _xp_to_next_level(self):
        if not self.player:
            return 100
        return max(100, self.player.level * 100)

    def _clamp_x(self, x):
        return max(1, min(self.width - 2, int(x)))

    def _clamp_y(self, y):
        return max(1, min(self.floor_y - 1, int(y)))
