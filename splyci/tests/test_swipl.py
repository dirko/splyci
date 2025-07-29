import os, sys, shutil

def test_probe_prolog():
    #os.environ.setdefault("PATH", "/opt/homebrew/opt/swi-prolog/bin:" + os.environ.get("PATH", ""))
    #os.environ["PATH"] = "/opt/homebrew/opt/swi-prolog/bin:" + os.environ["PATH"]
    print("sys.executable:", sys.executable)
    print("PATH:", os.environ.get("PATH"))
    print("SWI_HOME_DIR:", os.environ.get("SWI_HOME_DIR"))
    print("PROLOG_BINDIR:", os.environ.get("PROLOG_BINDIR"))
    print("PROLOG_LIBDIR:", os.environ.get("PROLOG_LIBDIR"))
    print("which swipl:", shutil.which("swipl"))
    try:
        from pyswip import Prolog
        Prolog()     # this is the point of failure
        print("✅ Prolog() succeeded")
    except Exception as e:
        print("❌ Prolog() raised:", type(e).__name__, e)
    assert True