#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2020 Edward Higgins <ed.higgins@york.ac.uk>
#
# Distributed under terms of the MIT license.

""" SIMULATION - Dataset simulation module

Description:
    simulation.py contains the code for the simulation task, which simulates
    pseudo-experimental datasets as characterised by the relevant parameters.

Contains:
    function simulate

Author:
    Edward Higgins

Version: 0.2.0
"""

from functools import reduce

import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np
import numpy.random as random

from images import ImageData
from spots import Spots
import trajectories


def simulate(params):

    # Make a spot array the same size as normal
    real_spots = [Spots(params.num_spots) for i in range(params.num_frames)]

    # initialise the spot co-ords
    real_spots[0].positions[:, 0] = random.rand(params.num_spots) * params.frame_size[0]
    real_spots[0].positions[:, 1] = random.rand(params.num_spots) * params.frame_size[1]
    real_spots[0].frame = 0

    # Simulate diffusion
    S = np.sqrt(2 * params.diffusionCoeff * params.frameTime) / params.pixelSize
    frame_start = 0
    frame_end = params.num_spots

    for frame in range(1, params.num_frames):
        real_spots[frame].frame = frame
        real_spots[frame].traj_num = real_spots[frame - 1].traj_num[:]
        real_spots[frame].positions = random.normal(
            real_spots[frame - 1].positions, S, (params.num_spots, 2)
        )

        if params.bleach_time > 0:
            bleached_spots = filter(
                lambda x: random.rand() < 1 / params.bleach_time,
                range(params.num_spots),
            )
            for spot in bleached_spots:
                real_spots[frame].positions[spot, 0] = (
                    random.rand(1) * params.frame_size[0]
                )
                real_spots[frame].positions[spot, 1] = (
                    random.rand(1) * params.frame_size[1]
                )
                next_traj_num = np.max(real_spots[frame].traj_num) + 1
                real_spots[frame].traj_num[spot] = next_traj_num

    # Simulate the image stack and save
    image = ImageData()
    image.initialise(params.num_frames, params.frame_size)

    x_pos, y_pos = np.meshgrid(range(params.frame_size[0]), range(params.frame_size[1]))
    for frame in range(params.num_frames):
        frame_data = np.zeros([params.frame_size[1], params.frame_size[0]]).astype(np.uint16)

        for spot in range(params.num_spots):
            spot_data = (
                (params.Isingle / (2 * np.pi * params.PSFwidth**2))
                * np.exp(
                    -(
                        (x_pos - real_spots[frame].positions[spot, 0]) ** 2
                        + (y_pos - real_spots[frame].positions[spot, 1]) ** 2
                    )
                    / (2 * params.PSFwidth ** 2)
                )
            ).astype(np.uint16)
            frame_data += spot_data
            real_spots[frame].spot_intensity[spot]=np.sum(spot_data)

        frame_data = random.poisson(frame_data)
        bg_noise = random.normal(params.BGmean, params.BGstd, [params.frame_size[1], params.frame_size[0]])
        frame_data += np.where(bg_noise > 0, bg_noise.astype(np.uint16), 0)
        image[frame] = frame_data

    real_trajs = trajectories.build_trajectories(real_spots, params)

    image.write(params)
    trajectories.write_trajectories(real_trajs, params,simulated=True)
    return image, real_trajs


def simulate_stepwise_bleaching(params):

    # Make a spot array the same size as normal
    real_spots = [Spots(params.num_spots) for i in range(params.num_frames)]

    # initialise the spot co-ords
    real_spots[0].positions[:, 0] = random.rand(params.num_spots) * params.frame_size[0]
    real_spots[0].positions[:, 1] = random.rand(params.num_spots) * params.frame_size[1]

    if params.num_spot_molecules is not None:
        n_mols = np.ones(params.num_spots, dtype='int')*int(params.num_spot_molecules)
    else:
        n_mols = random.randint(1, params.max_spot_molecules, params.num_spots)
    gtruth = np.copy(n_mols)
    print(gtruth)
    real_spots[0].spot_intensity[:] = params.Isingle*n_mols
    real_spots[0].frame = 1

    # Simulate the image stack
    image = ImageData()
    image.initialise(params.num_frames, params.frame_size)
    # Simulate diffusion
    S = 0
    frame_start = 0
    frame_end = params.num_spots

    for frame in range(1, params.num_frames):
        real_spots[frame].frame = frame
        real_spots[frame].spot_intensity[:] = params.Isingle * n_mols
        real_spots[frame].traj_num = real_spots[frame - 1].traj_num[:]
        real_spots[frame].positions = random.normal(
            real_spots[frame - 1].positions, S, (params.num_spots, 2)
        )
        # Photobleah some spots
        for i in range(params.num_spots):
            if n_mols[i] > 0:
                for j in range(n_mols[i]):
                    if random.rand() < params.p_bleach_per_frame:
                        n_mols[i] -= 1

    x_pos, y_pos = np.meshgrid(range(params.frame_size[1]), range(params.frame_size[0]))
    for frame in range(params.num_frames):
        frame_data = np.zeros(image.frame_size).astype(np.uint16)

        for spot in range(params.num_spots):
            frame_data += (
                (real_spots[frame].spot_intensity[spot] / (2 * np.pi * params.PSFwidth))
                * np.exp(
                    -(
                        (x_pos - real_spots[frame].positions[spot, 0]) ** 2
                        + (y_pos - real_spots[frame].positions[spot, 1]) ** 2
                    )
                    / (2 * params.PSFwidth ** 2)
                )
            ).astype(np.uint16)

        frame_data = random.poisson(frame_data)
        bg_noise = random.normal(params.BGmean, params.BGstd, params.frame_size)
        frame_data += np.where(bg_noise > 0, bg_noise.astype(np.uint16), 0)
        image[frame] = frame_data

    return image, gtruth