from dataclasses import dataclass

@dataclass(frozen=True)
class Action:
    id: str
    label: str
    description: str
    payload: dict

ACTIONS: list[Action] = [
    Action(
        id="A1",
        label="Increase font size",
        description="Step up base font scale by 12.5% for better readability.",
        payload={"font_scale_delta": 0.125},
    ),
    Action(
        id="A2",
        label="Increase contrast theme",
        description="Switch to a high-contrast palette to meet WCAG AAA contrast ratios.",
        payload={"contrast_level": "high"},
    ),
    Action(
        id="A3",
        label="Simplify layout",
        description="Reduce component density and remove non-essential elements.",
        payload={"density": "comfortable", "hide_nonessential": True},
    ),
    Action(
        id="A4",
        label="Increase hit target sizes",
        description="Enlarge interactive controls to meet 44x44 touch target minimum.",
        payload={"hit_target_min_px": 44},
    ),
    Action(
        id="A5",
        label="Enable reduced motion profile",
        description="Disable non-essential animations and transitions.",
        payload={"reduced_motion": True},
    ),
    Action(
        id="A6",
        label="No change",
        description="Keep the current interface state.",
        payload={},
    ),
]

ACTION_INDEX: dict[str, int] = {a.id: i for i, a in enumerate(ACTIONS)}

def get_action(action_id: str) -> Action:
    return ACTIONS[ACTION_INDEX[action_id]]

NUM_ACTIONS = len(ACTIONS)
