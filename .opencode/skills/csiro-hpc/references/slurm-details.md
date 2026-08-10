# Slurm advanced reference

## Table of contents

- Resource request options
- Job queues and partitions
- Interactive sessions
- Parallel and array jobs
- Job dependencies
- Environment modules
- GPU-specific options (Virga)
- Data transfer

## Resource request options

Key `sbatch` options:

- `--account=<O2D code>` - required project code.
- `--time=<HH:MM:SS>` - wall time limit. Formats: minutes, `HH:MM:SS`, `D-HH`, `D-HH:MM`.
- `--mem=<MB>` - total memory per node. Use `M` or `G` suffix (e.g. `--mem=32g`).
- `--mem-per-cpu=<MB>` - alternative to `--mem`, memory per CPU core.
- `--nodes=N` - number of nodes.
- `--ntasks-per-node=M` - CPU cores per node. Prefer this over `--ntasks` for multi-rank (MPI) work, to avoid fragmentation.
- `--cpus-per-task=N` - CPUs per task (for multi-threaded jobs). A single-process job that threads internally - a JVM, an OpenMP binary - wants `--ntasks=1 --cpus-per-task=N` instead: it is one task with N cores, not N ranks. The concept-port full run is one such job.
- `--gres=gpu:N` - number of GPUs per node (Virga only).
- `--mail-type=BEGIN,END,FAIL` - email notification events.
- `--mail-user=<email>` - notification email address.

Use `scontrol show job <jobid>` to check actual memory usage after a job completes.

## Job queues and partitions

Petrichor partitions:

| Partition | Max wall time | Notes                                                              |
| --------- | ------------- | ------------------------------------------------------------------ |
| `defq`    | 7 days        | Default partition.                                                 |
| `h2`      | 2 hours       | Higher priority, more nodes available.                             |
| `h24`     | 24 hours      | Medium priority.                                                   |
| `ext`     | 30 days       | Extended queue - use sparingly, jobs may be killed during outages. |
| `m1tb`    | 7 days        | 1 TB memory nodes (55 nodes).                                      |
| `m4tb`    | 7 days        | 4 TB memory nodes (4 nodes).                                       |
| `io`      | -             | Data transfer queue, routes to `petrichor-dm`.                     |

Virga partitions include accelerator and extended GPU (`extgpu`) queues. GPU partitions are automatically selected when `--gres=gpu` is requested.

Select a partition with `-p <name>` or `--partition=<name>`. For most jobs, omit this and let Slurm auto-select.

## Interactive sessions

Use `sinteractive` for interactive work:

```
sinteractive -n <tasks> -c <cpus-per-task> -t <time> -m <memory> -A <O2D code>
```

Options: `-n` tasks (default 1), `-c` CPUs per task (default 1), `-t` wall time (default 2:00:00), `-m` memory, `-p` partition, `-A` account, `-g` GPU request (e.g. `gpu:2`).

Memory for `sinteractive` is 512 MB per core by default.

Alternatively, use `salloc` directly:

```
salloc --ntasks-per-node=4 --mem=4gb --time=30:0 -A <O2D code> srun --pty bash
```

## Parallel and array jobs

### Array jobs

Submit parameterised jobs with a single script:

```
sbatch -a 1-20 myjob.q
```

Within the job, use `$SLURM_ARRAY_TASK_ID` to vary behaviour per array element.

### Loop-based submission

```bash
for X in $(seq 1 10); do sbatch --export X=$X myjob.q; done
```

### MPI jobs

Use `--nodes=N --ntasks-per-node=M` (prefer over `--ntasks` to avoid fragmentation). This is advice for **MPI**, where the ranks are the point; it does not apply to a single-process multi-threaded job:

```bash
module load openmpi
mpirun -np <total cores> ./my_mpi_app
```

### Shared memory / OpenMP jobs

```
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=16
```

## Job dependencies

Use `sdep` to chain jobs in sequence:

```
sdep job1.q job2.q job3.q
```

Or manually with `sbatch -d afterany:<jobid>`.

Options for `sdep`: `-f first_script` (run first, then rest in parallel), `-l last_script` (run after all others), `-t` (only proceed on success).

## Environment modules

- `module avail` - list available software.
- `module load <name>` or `module load <name>/<version>` - load a module.
- `module list` - show loaded modules.
- `module purge` - unload all modules.
- `module whatis <name>` - brief description.
- `module show <name>` - show environment changes.
- `module save <list>` / `module restore <list>` - save and restore module sets.

Always explicitly load modules in job scripts rather than relying on login environment.

## GPU-specific options (Virga)

Each Virga node has 4x NVIDIA H100 GPUs (94 GB HBM2e each).

Request GPUs with `--gres=gpu:<1-4>`. At least one CPU core must also be requested.

`CUDA_VISIBLE_DEVICES` is set automatically by Slurm to indicate allocated GPUs.

GPU compute mode is set to exclusive process by default - one process per GPU.

For multi-GPU single-task jobs:

```
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:3
```

## Data transfer

Use the data mover node for large transfers:

```
sinteractive -p io -t 2:00:00
```

This connects to `petrichor-dm.hpc.csiro.au`. From there, use `rsync` or `cp` to move data between `$SCRATCH3DIR`, `$STOREDIR`, and other systems.

`$STOREDIR` (the data store / DMF area) is only accessible from IO jobs on petrichor-dm.
