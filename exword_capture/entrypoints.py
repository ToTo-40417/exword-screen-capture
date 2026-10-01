def gui():
    try:
        from .app import main
    except ModuleNotFoundError as error:
        if error.name and error.name.startswith("PySide6"):
            raise SystemExit("GUI requires: pip install 'exword-screen-capture-cli[gui]'") from error
        raise
    main()
