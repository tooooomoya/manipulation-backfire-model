## Getting Started

Welcome to the VS Code Java world. Here is a guideline to help you get started to write Java code in Visual Studio Code.



```
javac -cp "$(find lib -name '*.jar' | tr '\n' ':')" -d bin src/**/*.java      
java -cp "$(find lib -name '*.jar' | tr '\n' ':'):bin" dynamics.OpinionDynamics
```

This simulation files require gephi library for visualization. 
gephi tool kits can be freely downloaded on the website. 

## Folder Structure

Make sure you create `results` folder as we do not upload them on github.

The workspace contains two folders by default, where:

- `src`: the folder to maintain sources
- `lib`: the folder to maintain dependencies

Meanwhile, the compiled output files will be generated in the `bin` folder by default.

> If you want to customize the folder structure, open `.vscode/settings.json` and update the related settings there.

## Dependency Management

The `JAVA PROJECTS` view allows you to manage your dependencies. More details can be found [here](https://github.com/microsoft/vscode-java-dependency#manage-dependencies).


## Python virtual environment

For using analysis python files, our requirments.txt may be useful

## Pararell Processing

Using shell file (run.sh) can make pararell processing possible. By rewiriting run.sh, you can change seeds to simulate concurrently. 

```
bash run.sh
```