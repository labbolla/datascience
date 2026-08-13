# Linear Programming Visualizer

Python project for modeling, solving and visualizing **two-variable Linear Programming problems** using the graphical vertex method.

The application allows the user to define an objective function and a set of linear constraints interactively, then identifies the feasible region, calculates its vertices, evaluates the objective function and displays the optimal solution graphically.

## Project Objective

The objective of the project is to provide a simple interactive tool for studying Linear Programming problems with two decision variables.

The program allows the user to:

- define the coefficients of the objective function;
- choose between maximization and minimization;
- define multiple linear constraints;
- include non-negativity restrictions;
- calculate intersections between constraint boundaries;
- identify feasible vertices;
- evaluate the objective function at each feasible vertex;
- identify the optimal objective value;
- visualize constraints, vertices, feasible region and optimal point.

## User Input

When the notebook is executed, the program requests the Linear Programming problem step by step.

### Objective Function

The user enters the coefficients of:

```text
Z = c1*x1 + c2*x2
```

For example:

```text
2,1
```

corresponds to:

```text
Z = 2*x1 + 1*x2
```

The user can then choose:

```text
maximize
```

or:

```text
minimize
```

## Constraints

For each constraint, the user defines:

- the coefficients of `x1` and `x2`;
- the relationship operator;
- the right-hand-side value.

The application supports:

```text
<=
>=
=
```

The program also considers the non-negativity constraints:

```text
x1 >= 0
x2 >= 0
```

## Processing Workflow

```text
Objective Function Input
        ↓
Optimization Sense
        ↓
Constraint Input
        ↓
Constraint Standardization
        ↓
Intersection Calculation
        ↓
Feasibility Check
        ↓
Feasible Vertices
        ↓
Objective Function Evaluation
        ↓
Optimal Value Identification
        ↓
Graphical Visualization
```

## Vertex Method

For a two-variable Linear Programming problem, an optimal solution can be found among the vertices of the feasible region when an optimum exists.

The application calculates the intersections between constraint boundaries using linear algebra.

Each candidate point is then checked against all constraints. Only points belonging to the feasible region are retained.

The objective function is evaluated at every feasible vertex.

For a maximization problem, the largest objective value is selected.

For a minimization problem, the smallest objective value is selected.

## Example

The notebook includes an example with the following objective function:

```text
Maximize Z = 2*x1 + x2
```

subject to:

```text
6*x1 + 3*x2 >= 450
6*x1 + 3*x2 <= 480
2*x1 + 4*x2 >= 450
2*x1 + 4*x2 <= 480

x1 >= 0
x2 >= 0
```

The application identifies the feasible vertices and evaluates the objective function at each point.

| Vertex | Objective Value |
|---|---:|
| (31.67, 96.67) | 160 |
| (26.67, 106.67) | 160 |
| (20.00, 110.00) | 150 |
| (25.00, 100.00) | 150 |

The optimal objective value is:

```text
Z = 160
```

Two feasible vertices reach the same optimal value.

## Feasible Region Visualization

The application generates a graphical representation containing:

- constraint boundary lines;
- feasible vertices;
- the feasible region;
- the optimal solution.

The feasible polygon is constructed using `scipy.spatial.ConvexHull` and visualized with Matplotlib.

This graphical representation makes it possible to understand how the constraints interact to define the solution space.

## Main Functions

### Input

```python
get_objective_function()
get_optimization_sense()
get_constraints()
```

Collect the objective function, optimization direction and constraints from the user.

### Problem Representation

```python
print_linear_program()
standardize_constraints()
```

Display and standardize the mathematical problem.

### Geometry and Feasibility

```python
find_intersection()
is_valid_vertex()
calculate_vertices()
```

Calculate intersections between constraints and determine which points belong to the feasible region.

### Optimization

```python
check_solutions()
```

Evaluate the objective function at the feasible vertices and identify the optimal value.

### Visualization

```python
plot_with_scipy()
```

Generate the graphical representation of the constraints, feasible region, vertices and optimal point.

## Technologies

- Python
- NumPy
- SciPy
- Matplotlib
- Jupyter Notebook / Google Colab

## Mathematical & Computational Concepts

- Linear Programming
- Operations Research
- Objective Functions
- Linear Constraints
- Maximization and Minimization
- Feasible Regions
- Vertex Method
- Linear Systems
- Matrix Operations
- Constraint Feasibility
- Convex Hull
- Computational Geometry
- Data Visualization

## Limitations

The current implementation is designed for **Linear Programming problems with two decision variables**, since the feasible region and optimal solution are represented in a two-dimensional graph.

The optimization procedure uses explicit calculation and evaluation of feasible vertices rather than relying on a general-purpose optimization solver.

The project is therefore primarily intended as an analytical and educational tool for exploring the geometry and logic behind Linear Programming.

## Possible Improvements

Future improvements could include:

- integration with `scipy.optimize.linprog`;
- support for problems with more than two decision variables;
- automatic identification of infeasible problems;
- detection of unbounded solutions;
- improved handling of equality constraints;
- automatic identification of multiple optimal solutions;
- interactive graphical controls;
- export of optimization results.

## File

📓 [Jupyter Notebook](linear_programming_visualizer.ipynb)
