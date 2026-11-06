"""What the Poetry Camera can and cannot do, in propkit's capability-discovery shape (served at GET /api/capabilities).

Add an entry only when the code for it exists; planned or commonly expected things are listed with installed=False and a reason.
tests/test_capabilities.py checks every installed entry against the code.
"""

CAPABILITIES = [
    {"id": "poem.photo", "label": "Photo to poem", "installed": True, "since": "1.0.0",
     "description": "A press of the shutter button takes a photo; a vision AI model (Anthropic or OpenAI, with the other as backup, then a canned poem) "
                    "writes one poem about the people and scene in the photo.",
     "plain": ["Write a poem about whoever is in front of the camera", "What happens when someone presses the button?"],
     "example": "", "ops": []},
    {"id": "poem.formats", "label": "Poem formats", "installed": True, "since": "1.0.0",
     "description": "The poem can be a limerick, ballad stanza, rhyming couplets, clerihew or sonnet; the prompt and an optional demo context "
                    "(who is at the event) are editable on the AI tab.",
     "plain": ["Make the poems limericks tonight", "Tell the camera this is a company holiday party"],
     "example": "", "ops": []},
    {"id": "print.thermal", "label": "Print on a thermal strip", "installed": True, "since": "1.0.0",
     "description": "The poem is printed on a small Bluetooth thermal printer (MX06 cat printer); a network printer can be selected instead. "
                    "A test print is on the Settings tab. Needs paper and the printer switched on.",
     "plain": ["Print a test strip", "Is the printer ready?"],
     "example": "", "ops": []},
    {"id": "zoltar.lucky_number", "label": "Lucky number for Zoltar", "installed": True, "since": "1.0.0",
     "description": "Each poem is sent to the Zoltar prop with a lucky number (22 to 99, no 0 or 1 digits, not reused within 24 hours). "
                    "If Zoltar accepts it, the number is printed under the poem so the guest can tell Zoltar, who reads the poem aloud. "
                    "Switch, address and shared token are on the Settings tab; if Zoltar is unreachable the poem prints without a number.",
     "plain": ["Turn the Zoltar lucky number off", "Why did this poem print without a number?"],
     "example": "", "ops": []},
    {"id": "ai.settings", "label": "AI keys, model and health check", "installed": True, "since": "1.0.0",
     "description": "Provider, model, prompt and keys are set on the AI tab, with a test using a chosen photo (text only, no printing) "
                    "and a daily key and model check. A banner shows when the last poems were canned backups.",
     "plain": ["Switch the camera to a different model", "Is the AI key still working?"],
     "example": "", "ops": []},
    {"id": "print.photo", "label": "Print the photo itself", "installed": False, "since": "",
     "description": "Print the guest's photo on the strip.", "reason": "Only planned (PHOTO_PRINTER_PLAN.md); the camera prints poems only.",
     "plain": ["Print the photo with the poem"], "example": "", "ops": []},
    {"id": "poem.read_aloud", "label": "Speak the poem", "installed": False, "since": "",
     "description": "Read the poem aloud from the camera.", "reason": "The camera has no speaker; Zoltar reads poems aloud via the lucky number.",
     "plain": ["Have the camera read the poem out loud"], "example": "", "ops": []},
    {"id": "trigger.schedule", "label": "Timed or remote trigger", "installed": False, "since": "",
     "description": "Take a poem photo at a set time or from the web.", "reason": "Only the physical shutter button starts a poem.",
     "plain": ["Take a poem photo every ten minutes"], "example": "", "ops": []},
]


def capabilities():
    return [dict(c) for c in CAPABILITIES]
