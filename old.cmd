@echo off

rem Get the command line argument
set option=%1
if /i "%1"=="-h" goto usage
if /i "%1"=="--help" goto usage

set venv_activation=.\\build_venv\\Scripts\\activate

rem Check if the option is -score
if /i "%option%"=="--score" (
    rem Execute instructions for -check option
    echo Scoring code...
    call :setup_venv_if_not_there
    call :check_maintainability_and_complexity
) else (
    rem Check if the option is -check
    if /i "%option%"=="--check" (
        rem Execute instructions for -check option
        echo Checking code...
        call :setup_venv_if_not_there
        call :check_types_and_conventions
    ) else (
        rem Check if the option is -reformat
        if /i "%option%"=="--reformat" (
            rem Execute instructions for -reformat option
            echo Reformatting code...
            call :setup_venv_if_not_there
            call :reformat
        ) else (
            rem Check if the option is -build
            if /i "%option%"=="--build" (
                rem Execute instructions for -build option
                echo Building Package...
                call :setup_venv_if_not_there
                call :build_install_and_test
            ) else (
                if /i "%option%"=="--all" (
                    rem If no option is given, execute all three
                    call :setup_venv_if_not_there
                    echo Reformatting code...
                    call :reformat
                    echo Checking code...
                    call :check_types_and_conventions
                    call :check_maintainability_and_complexity
                    echo Building code...
                    call :build_install_and_test
                    call :install_in_user_venv
                ) else (
                    call :usage
                )
            )
        )
    )
)

echo Done, I'm fucking off now!
goto :eof

:setup_venv_if_not_there
    IF EXIST %venv_activation% (
        echo using %venv_activation% as venv to build
    ) ELSE (
        rem install all dependencies (we dont care about version but update if there is a newer version)
        echo creating %venv_activation% as venv to build
        call .\\venv\\Scripts\\activate & py -m venv build_venv
        call %venv_activation% & py -m pip install --upgrade pip
        call %venv_activation% & pip install -r requirements.txt
        call %venv_activation% & pip install --upgrade isort pipreqs black build radon pylint mypy lxml toml
    )
    goto :eof

:reformat
    rem reformat code
    echo isort sorting your imports (does not remove unrequired ones):
    call %venv_activation% & isort .
    echo pipreqs updating your requirements.txt (with compatibility mode package~=A.B.C):
    call %venv_activation% & pipreqs --mode compat --force --ignore venv,build_venv --savepath requirements.txt .\\src
    call :update_pyproject_toml_from_requirements
    echo reformatting your code with black:
    call %venv_activation% & black .
    goto :eof

:check_types_and_conventions
    rem check code quality
    echo mypy results (type checking):
    call %venv_activation% & mypy .\\src\\.
    echo pylint results (are there any violated conventions):
    call %venv_activation% & pylint .\\src\\.
    goto :eof

:check_maintainability_and_complexity
    rem check code maintainability and complexity
    echo maintainability as given by radon (score as number and Rank as letter)
    call %venv_activation% & radon mi .\\src\\.
    echo cyclomatic complexity as given by radon (score as number and Rank as letter)
    call %venv_activation% & radon cc .\\src\\.
    goto :eof

:build_install_and_test
    echo building your package (that is in .\\src)
    rd /s /q "dist"
    call %venv_activation% & py -m build
    echo installing your package (using the .whl in dist)
    for /f "delims=" %%i in ('dir .\\dist\\*.whl /s /b') do set "wheel_file=%%i"
    call %venv_activation% & pip install %wheel_file% --force-reinstall
    echo running the (unit)-tests in your installed package:
    call %venv_activation% & py -m unittest discover
    goto :eof

:usage
    rem Display help message
    echo.
    echo Usage: script.cmd [OPTION]
    echo.
    echo Options:
    echo --check        Check code
    echo --reformat     Reformat code
    echo --score        Score code
    echo --build        Build package
    echo --all          execute --reformat, --check, --score and --build
    echo -h, --help   Display this help message
    echo.
    goto :eof


:update_pyproject_toml_from_requirements
    call python -c "import toml; original_toml = toml.load('pyproject.toml'); original_toml['project']['dependencies'] = list(map(str.strip, map(str, open('requirements.txt', 'r').readlines()))); toml.dump(original_toml, open('pyproject.toml', 'w')); print('updated pyproject.toml with requirements.txt'); quit()"
    goto :eof

:install_in_user_venv
    for /f "delims=" %%i in ('dir .\\dist\\*.whl /s /b') do set "wheel_file=%%i"
    call venv\Scripts\activate & pip install %wheel_file% --force-reinstall
