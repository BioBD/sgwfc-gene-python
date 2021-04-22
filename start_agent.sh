#!/usr/bin/env bash
prefect agent docker start --no-pull --no-docker-interface --volume $HOME --volume `pwd`/workflow:/workflow --volume `pwd`/input:/workflow/input --volume `pwd`/result:/workflow/result -l `hostname` --log-level DEBUG