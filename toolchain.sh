#!/bin/bash

option=$1

venv_activation=./build_venv/bin/activate

function usage {
  # Display help message
  echo ""
  echo "POOR MANS BUILD PIPELINE by"
  echo "flfluchs@student.ethz.ch"
  echo "for python>=3.10 projects where a venv is available (at venv)"
  echo "your code should reside in ./src"
  echo ""
  echo "Usage: script.sh [OPTION]"
  echo ""
  echo "Options:"
  echo "--check        Check code"
  echo "--reformat     Reformat code"
  echo "--score        Score code"
  echo "--build        Build package"
  echo "--install      Install package (in venv)"
  echo "--all          execute --reformat, --check, --score, --build, and --install"
  echo "--test         Run unit tests"
  echo "-h, --help     Display this help message"
  echo ""
}

function setup_venv_if_not_there {
  if [ -f "$venv_activation" ]; then
    echo "Using $venv_activation as venv to build"
  else
    echo "Creating $venv_activation as venv to build"
    python3 -m venv build_venv
    source $venv_activation
    pip install --upgrade pip
    pip install -r requirements.txt
    pip install --upgrade isort pipreqs black build radon pylint mypy lxml toml
  fi
}

function reformat {
  echo "Isort sorting your imports (does not remove unrequired ones):"
  source $venv_activation
  isort .
  echo "Pipreqs updating your requirements.txt (with compatibility mode package~=A.B.C):"
  pipreqs --mode compat --force --ignore venv,build_venv --savepath requirements.txt ./src
  update_pyproject_toml_from_requirements
  echo "Reformatting your code with black:"
  black .
}

function check_types_and_conventions {
  echo "Mypy results (type checking):"
  source $venv_activation
  mypy ./src/.
  echo "Pylint results (are there any violated conventions):"
  pylint ./src/.
}

function check_maintainability_and_complexity {
  echo "maintainability as given by radon (score as number and Rank as letter)"
  source $venv_activation
  radon mi ./src/
  echo "cyclomatic complexity as given by radon (score as number and Rank as letter)"
  source $venv_activation
  radon cc ./src/
}

function build_install_and_test {
  echo "building your package (that is in ./src)"
  rm -rf dist
  source $venv_activation
  python -m build
  echo "installing your package (using the .whl in dist)"
  wheel_file=$(ls ./dist/*.whl)
  pip install $wheel_file --force-reinstall
  run_tests
}

function update_pyproject_toml_from_requirements {
  python -c "import toml; original_toml = toml.load('pyproject.toml'); original_toml['project']['dependencies'] = list(map(str.strip, map(str, open('requirements.txt', 'r').readlines()))); toml.dump(original_toml, open('pyproject.toml', 'w')); print('updated pyproject.toml with requirements.txt'); quit()"
}

function install_in_user_venv {
  wheel_file=$(ls ./dist/*.whl)
  source venv/bin/activate
  pip install $wheel_file --force-reinstall
}

function run_tests {
  echo "running the (unit)-tests in your installed package:"
  source $venv_activation
  python -m unittest discover
}

if [ "$option" == "-h" ] || [ "$option" == "--help" ]; then
    usage
elif [ "$option" == "--score" ]; then
  echo "Scoring code..."
  setup_venv_if_not_there
  check_maintainability_and_complexity
elif [ "$option" == "--check" ]; then
  echo "Checking code..."
  setup_venv_if_not_there
  check_types_and_conventions
elif [ "$option" == "--reformat" ]; then
  echo "Reformatting code..."
  setup_venv_if_not_there
  reformat
elif [ "$option" == "--build" ]; then
  echo "Building Package..."
  setup_venv_if_not_there
  build_install_and_test
elif [ "$option" == "--install" ]; then
  echo "Installing Package..."
  install_in_user_venv
elif [ "$option" == "--all" ]; then
  setup_venv_if_not_there
  reformat
  check_types_and_conventions
  check_maintainability_and_complexity
  build_install_and_test
  install_in_user_venv
elif [ "$option" == "--test" ]; then
  echo "Running tests..."
  setup_venv_if_not_there
  run_tests
fi
