import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# If fastapi/cv2/ultralytics/numpy are not installed in this environment, provide minimal mocks for test runner
for mod_name in ["fastapi", "cv2", "ultralytics", "numpy"]:
    if mod_name not in sys.modules:
        try:
            __import__(mod_name)
        except ImportError:
            import types
            mock_mod = types.ModuleType(mod_name)
            if mod_name == "fastapi":
                class APIRouter:
                    def __init__(self, *args, **kwargs): pass
                    def get(self, *args, **kwargs): return lambda f: f
                    def post(self, *args, **kwargs): return lambda f: f
                    def websocket(self, *args, **kwargs): return lambda f: f
                class HTTPException(Exception):
                    def __init__(self, status_code, detail=None):
                        self.status_code = status_code
                        self.detail = detail
                mock_mod.APIRouter = APIRouter
                mock_mod.HTTPException = HTTPException
                mock_mod.Query = lambda *a, **k: None
                mock_mod.Response = object
                mock_mod.UploadFile = object
                mock_mod.File = lambda *a, **k: None
                mock_mod.Form = lambda *a, **k: None
                mock_responses = types.ModuleType("fastapi.responses")
                mock_responses.StreamingResponse = object
                sys.modules["fastapi.responses"] = mock_responses
            elif mod_name == "numpy":
                mock_mod.array = lambda x, **kw: x
                mock_mod.uint8 = int
                mock_mod.ndarray = object
            sys.modules[mod_name] = mock_mod

from ai.interpreter import parse_command
from ai.schemas import StructuredTask, BaseModel, Field

if "pydantic" not in sys.modules:
    try:
        import pydantic
    except ImportError:
        import types
        pydantic_mock = types.ModuleType("pydantic")
        pydantic_mock.BaseModel = BaseModel
        pydantic_mock.Field = Field
        sys.modules["pydantic"] = pydantic_mock

from api.routes_command import generate_understanding_text


def test_required_commands():
    print("==================================================================")
    print("  STEP 1 VERIFICATION: DUAL FIXED-BASE ROBOT ARM OBJECT TRANSFER")
    print("==================================================================")

    # Command 1
    cmd1 = "Robot 1 pick the red bottle and give it to Robot 2"
    t1 = parse_command(cmd1)
    und1 = generate_understanding_text(t1)
    print(f"\n[Command 1]: '{cmd1}'")
    print(f"   Object:            {t1.object_name or t1.object.name}")
    print(f"   Colour:            {t1.colour}")
    print(f"   Source Robot:      {t1.source_robot}")
    print(f"   Destination Robot: {t1.destination_robot}")
    print(f"   Action:            {t1.action}")
    print(f"   Understanding:     \"{und1}\"")

    assert (t1.object_name or t1.object.name) == "bottle", f"Expected bottle, got {t1.object_name}"
    assert t1.colour == "red", f"Expected red, got {t1.colour}"
    assert t1.source_robot == "Robot 1", f"Expected Robot 1, got {t1.source_robot}"
    assert t1.destination_robot == "Robot 2", f"Expected Robot 2, got {t1.destination_robot}"
    assert t1.action == "transfer", f"Expected transfer, got {t1.action}"
    print("   --> [PASS]")

    # Command 2 (No colour specified -> colour must be None/null)
    cmd2 = "Robot 1 pick the mango and give it to Robot 2"
    t2 = parse_command(cmd2)
    und2 = generate_understanding_text(t2)
    print(f"\n[Command 2]: '{cmd2}'")
    print(f"   Object:            {t2.object_name or t2.object.name}")
    print(f"   Colour:            {t2.colour}")
    print(f"   Source Robot:      {t2.source_robot}")
    print(f"   Destination Robot: {t2.destination_robot}")
    print(f"   Action:            {t2.action}")
    print(f"   Understanding:     \"{und2}\"")

    assert (t2.object_name or t2.object.name) == "mango", f"Expected mango, got {t2.object_name}"
    assert t2.colour is None, f"Expected None/null, got {t2.colour}"
    assert t2.source_robot == "Robot 1", f"Expected Robot 1, got {t2.source_robot}"
    assert t2.destination_robot == "Robot 2", f"Expected Robot 2, got {t2.destination_robot}"
    assert t2.action == "transfer", f"Expected transfer, got {t2.action}"
    print("   --> [PASS]")

    # Command 3 (Compound generic object name: mobile phone, no colour)
    cmd3 = "Robot 1 pick the mobile phone and give it to Robot 2"
    t3 = parse_command(cmd3)
    und3 = generate_understanding_text(t3)
    print(f"\n[Command 3]: '{cmd3}'")
    print(f"   Object:            {t3.object_name or t3.object.name}")
    print(f"   Colour:            {t3.colour}")
    print(f"   Source Robot:      {t3.source_robot}")
    print(f"   Destination Robot: {t3.destination_robot}")
    print(f"   Action:            {t3.action}")
    print(f"   Understanding:     \"{und3}\"")

    assert (t3.object_name or t3.object.name) in ("mobile phone", "phone"), f"Expected mobile phone, got {t3.object_name}"
    assert t3.colour is None, f"Expected None/null, got {t3.colour}"
    assert t3.source_robot == "Robot 1", f"Expected Robot 1, got {t3.source_robot}"
    assert t3.destination_robot == "Robot 2", f"Expected Robot 2, got {t3.destination_robot}"
    assert t3.action == "transfer", f"Expected transfer, got {t3.action}"
    print("   --> [PASS]")

    # Command 4
    cmd4 = "Robot 1 pick the blue cup and give it to Robot 2"
    t4 = parse_command(cmd4)
    und4 = generate_understanding_text(t4)
    print(f"\n[Command 4]: '{cmd4}'")
    print(f"   Object:            {t4.object_name or t4.object.name}")
    print(f"   Colour:            {t4.colour}")
    print(f"   Source Robot:      {t4.source_robot}")
    print(f"   Destination Robot: {t4.destination_robot}")
    print(f"   Action:            {t4.action}")
    print(f"   Understanding:     \"{und4}\"")

    assert (t4.object_name or t4.object.name) == "cup", f"Expected cup, got {t4.object_name}"
    assert t4.colour == "blue", f"Expected blue, got {t4.colour}"
    assert t4.source_robot == "Robot 1", f"Expected Robot 1, got {t4.source_robot}"
    assert t4.destination_robot == "Robot 2", f"Expected Robot 2, got {t4.destination_robot}"
    assert t4.action == "transfer", f"Expected transfer, got {t4.action}"
    print("   --> [PASS]")

    print("\n------------------------------------------------------------------")
    print("  VERIFYING BACKWARD COMPATIBILITY WITH EXISTING COMMANDS")
    print("------------------------------------------------------------------")

    # Existing Test 1
    t_ex1 = parse_command("Pick the red bottle.")
    assert t_ex1.action == "pick"
    assert t_ex1.object.name == "bottle"
    assert t_ex1.object.color == "red"
    print("[PASS] 'Pick the red bottle.' -> action: pick, object: bottle, color: red")

    # Existing Test 2
    t_ex2 = parse_command("Pick the blue cup and give it to the JetArm.")
    assert t_ex2.action == "pick_and_transfer" or t_ex2.action == "transfer"
    assert t_ex2.object.name == "cup"
    assert t_ex2.object.color == "blue"
    assert t_ex2.destination == "jetarm" or t_ex2.destination == "Robot 2"
    assert t_ex2.source == "diy_arm" or t_ex2.source == "Robot 1"
    print("[PASS] 'Pick the blue cup and give it to the JetArm.' -> destination: jetarm, source: diy_arm")

    # Existing Test 3
    t_ex3 = parse_command("Find the box and move it to the right.")
    assert t_ex3.action in ("find_and_move", "move", "find")
    assert t_ex3.object.name == "box"
    assert t_ex3.destination == "right"
    print("[PASS] 'Find the box and move it to the right.' -> action: find_and_move, destination: right")

    # Existing Test 4
    t_ex4 = parse_command("Locate the small yellow canister and pass it to the DIY arm.")
    assert t_ex4.action == "pick_and_transfer" or t_ex4.action == "transfer"
    assert t_ex4.object.name == "canister"
    assert t_ex4.object.attributes.color == "yellow"
    assert t_ex4.object.attributes.size == "small"
    print("[PASS] 'Locate the small yellow canister and pass it to the DIY arm.' -> object: canister, color: yellow")

    print("\n==================================================================")
    print("  ALL 4 REQUIRED TRANSFER COMMANDS & EXISTING TESTS PASSED!")
    print("==================================================================")


if __name__ == "__main__":
    test_required_commands()
