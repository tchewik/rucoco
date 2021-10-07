from functools import partial
from itertools import chain, cycle
import tkinter as tk
from tkinter import ttk
from typing import *

from coref_markup.const import *
from coref_markup.markup import *
from coref_markup.markup_text import *
from coref_markup.markup_label import *
from coref_markup import utils


# TODO: merge entities
# TODO: scroll entities
# TODO: open files
# TODO: save files
# TODO: delete entity (select and press delete; should there be a Button?)
# TODO: delete spans (how?)
# TODO: config (annotator name, what else?)
# TODO: span and entity texts in error messages (custom Exception class to pass data)
# TODO: CRITICAL: self within self is absolutely invisible -- possible solution: individual tag for each span
# TODO: reorganize code
# TODO: docstrings
# TODO: mypy and pylint


class Application(ttk.Frame):
    def __init__(self, master: tk.Tk):
        super().__init__(master)
        self.master = master
        self.pack()

        self.__config = {"name": "annotator"}
        self.__text = "Привет, это Вася! Я давно хотел тебе написать, Иван. Как у тебя дела? У меня норм все вот. Мы." #* 100
        self.markup = Markup()
        self.markup.new_entity(("1.12", "1.16"))
        self.markup.add_span_to_entity(("1.18", "1.19"), 0)
        self.markup.new_entity(("1.32", "1.36"))
        self.markup.new_entity(("1.47", "1.51"))
        self.markup.merge(self.markup._entities[1], self.markup._entities[2])

        # self.__markup.merge((12, 16), (18, 19))
        # self.__markup.merge((32, 36), (47, 51))
        i = self.markup.new_entity(("1.91", "1.93"), True)
        self.markup.merge(self.markup._entities[i], self.markup._entities[0])
        self.markup.merge(self.markup._entities[i], self.markup._entities[1])

        self.entity2label: Dict[int, MarkupLabel] = {}
        self.selected_entity: Optional[int] = None

        self.build_colors()
        self.build_widgets()

        #######################################################################
        # for entity in self.markup._entities:
        #     if entity is not None:
        #         for start, end in entity.spans:
        #             self.text_box.tag_add(f"entity#{entity.idx}", start, end)
        #######################################################################

        self.render_entities()

    def add_span_to_entity(self, span: Span, entity_idx: int):
        try:
            self.markup.add_span_to_entity(span, entity_idx)
            self.render_entities()
        except RuntimeError as e:
            self.set_status(e.args[0])

    def build_colors(self):
        self.all_colors = cycle(utils.get_colors())
        self.entity2color: Dict[int, str] = {}
        self.color_stack: List[str] = []

    def build_widgets(self):
        """
        Only making the following visible as instance attributes:
            self.entity_panel
            self.multi_entity_panel
            self.status_bar
            self.text_box
        """
        menubar = tk.Menu(self)
        menubar.add_command(label="Open")
        menubar.add_command(label="Save")
        self.master.configure(menu=menubar)

        main_frame = ttk.Frame(self)
        main_frame.pack(side="top", fill="both")

        status_bar = ttk.Label(self)
        status_bar.pack(side="bottom", fill="x")

        text_box = MarkupText(main_frame, wrap="word")
        text_box.set_text(self.__text) ########################################
        text_box.bind("<ButtonRelease>", self.mouse_handler_text)
        # text_box.bind("<<Selection>>", self.select_handler)

        text_box.pack(side="left")

        panel = ttk.Frame(main_frame)
        panel.pack(side="right", fill="y")

        text_box_scroller = ttk.Scrollbar(main_frame, command=text_box.yview)
        text_box_scroller.pack(side="left", after=text_box, before=panel, fill="y")
        text_box["yscrollcommand"] = text_box_scroller.set

        separator = ttk.Separator(main_frame, orient="vertical")
        separator.pack(side="left", after=text_box_scroller, before=panel, fill="y")

        entity_panel = ttk.Frame(panel)
        entity_panel.bind("<ButtonRelease>", self.mouse_handler_panel)
        entity_panel.pack(side="left", fill="y")

        separator = ttk.Separator(panel, orient="vertical")
        separator.pack(side="left", after=entity_panel, fill="y")

        multi_entity_panel = ttk.Frame(panel)
        multi_entity_panel.bind("<ButtonRelease>", self.mouse_handler_panel)
        multi_entity_panel.pack(side="right", fill="y")

        entity_panel_label = ttk.Label(entity_panel, text="Entities")
        entity_panel_label.pack(side="top")

        mentity_panel_label = ttk.Label(multi_entity_panel, text="mEntities")
        mentity_panel_label.pack(side="top")

        new_entity_button = ttk.Button(entity_panel, text="New Entity", command=self.new_entity)
        new_entity_button.pack(side="bottom")

        new_mentity_button = ttk.Button(multi_entity_panel, text="New mEntity",
                                        command=partial(self.new_entity, multi=True))
        new_mentity_button.pack(side="bottom")

        # Registering attributes
        self.entity_panel = entity_panel
        self.multi_entity_panel = multi_entity_panel
        self.status_bar = status_bar
        self.text_box = text_box

    def mouse_handler_label(self, event: tk.Event, entity_idx: int):
        if event.num == LEFT_MOUSECLICK:
            if self.text_box.selection_exists():
                self.add_span_to_entity(self.text_box.get_selection_indices(), entity_idx)
                self.text_box.clear_selection()
            elif self.selected_entity == entity_idx:
                self.entity2label[self.selected_entity].unselect()
                self.selected_entity = None
            else:
                if self.selected_entity is not None:
                    self.entity2label[self.selected_entity].unselect()
                self.selected_entity = entity_idx
                self.entity2label[self.selected_entity].select()

    def mouse_handler_panel(self, event: tk.Event):
        if event.num == LEFT_MOUSECLICK and self.selected_entity is not None:
            self.entity2label[self.selected_entity].unselect()
            self.selected_entity = None

    def mouse_handler_text(self, event: tk.Event):
        if event.num == LEFT_MOUSECLICK and self.selected_entity is not None and self.text_box.selection_exists():
            self.add_span_to_entity(self.text_box.get_selection_indices(), self.selected_entity)
            self.text_box.clear_selection()

    def mouse_hover_handler(self, event: tk.Event, entity_idx: int, underline: bool = True):
        if event.type is tk.EventType.Enter:
            for span in self.markup.get_spans(entity_idx):
                self.text_box.tag_add(f"h{entity_idx}", *span)
            self.text_box.tag_configure(f"h{entity_idx}", bgstipple="gray50", underline=underline)
            self.entity2label[entity_idx].enter()
        else:
            self.text_box.tag_delete(f"h{entity_idx}")
            self.entity2label[entity_idx].leave()

        if self.markup.is_multi_entity(entity_idx):
            for inner_entity_idx in self.markup.get_inner_entities(entity_idx):
                self.mouse_hover_handler(event, inner_entity_idx, underline=False)

    def get_entity_color(self, entity_idx: int) -> str:
        if entity_idx not in self.entity2color:
            self.entity2color[entity_idx] = self.color_stack.pop() if self.color_stack else next(self.all_colors)
        return self.entity2color[entity_idx]

    def new_entity(self, multi: bool = False):
        try:
            start, end = self.text_box.get_selection_indices()
            self.text_box.clear_selection()
            self.markup.new_entity((start, end), multi=multi)
            self.render_entities()
        except RuntimeError as e:
            self.set_status(e.args[0])

    def render_entities(self):
        for child in chain(self.entity_panel.winfo_children(), self.multi_entity_panel.winfo_children()):
            if isinstance(child, MarkupLabel):
                child.destroy()
        self.text_box.clear_tags()

        all_spans: List[Tuple[Span, int]] = []
        for entity_idx in self.markup.get_entities():
            color = self.get_entity_color(entity_idx)

            # Highlight spans in the text
            spans = sorted(self.markup.get_spans(entity_idx))
            for span in spans:
                all_spans.append((span, entity_idx))
                self.text_box.tag_add(f"e{entity_idx}", *span)
            self.text_box.tag_configure(f"e{entity_idx}", background=color)

            # Add labels to the right panel
            label_text = self.text_box.get(*spans[0])[:32]
            if isinstance(self.markup._entities[entity_idx], MultiEntity):
                placement = self.multi_entity_panel
            else:
                placement = self.entity_panel
            label = MarkupLabel(placement, text=label_text, background=color, borderwidth=0, relief="solid")
            label.pack(side="top")
            label.bind("<Enter>", partial(self.mouse_hover_handler, entity_idx=entity_idx))
            label.bind("<Leave>", partial(self.mouse_hover_handler, entity_idx=entity_idx))
            label.bind("<ButtonRelease>", partial(self.mouse_handler_label, entity_idx=entity_idx))
            self.entity2label[entity_idx] = label

        # Because tkinter doesn't support several layers of tags, manually
        # set the color again for overlapping regions
        all_spans.sort(key=lambda x: self.text_box.count(*x[0], "chars"), reverse=True)  # longest spans first
        for span, entity_idx in all_spans:
            tags = [tag for tag in self.text_box.tag_names(span[0]) if tag.startswith("e")]
            print(self.text_box.get(*span), tags)
            if len(tags) > 1:
                self.text_box.tag_add(f"{span[0]}e{entity_idx}", *span)
                self.text_box.tag_configure(f"{span[0]}e{entity_idx}", background=self.get_entity_color(entity_idx)) #utils.get_shade(self.get_entity_color(entity_idx), 0.2))

        if self.selected_entity is not None:
            self.entity2label[self.selected_entity].select()

    # def select_handler(self, event: tk.Event):
    #     print("selection")

    def set_status(self, message: str, duration: int = 5000):
        self.status_bar.configure(text=message)
        self.after(duration, lambda: self.status_bar.configure(text=""))