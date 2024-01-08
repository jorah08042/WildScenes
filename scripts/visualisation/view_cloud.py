import argparse
import sys
import os
import open3d as o3d
import numpy as np
from pynput import keyboard
import time
from threading import Thread
from glob import glob
from pathlib import Path

from wildscenes.tools.utils import cidx_2_rgb


root_dir = Path(__file__).parent.parent.parent
sys.path.append(str(root_dir))


'''
view_cloud.py

This script allows for viewing 3D labeled point clouds. Input argument options provided are:
--viewpoint
    Options: BEV, FPV. Displays the cloud from either a birds eye view or perspective view
--loadidx

--sequential

--video

'''


def load_pcd(cloud, labels, fpv=False):
    # Load points
    pcd = o3d.geometry.PointCloud()
    points = np.fromfile(cloud, dtype=np.float32).reshape(-1,3)
    # Load colours
    labels = np.fromfile(labels, dtype = np.int32)
    # Need to remap colours to the output palette
    colors = np.array([list(cidx_2_rgb[x]) for x in labels]) / 255

    if fpv:
        index = points[:, 0] >= 0
        points = points[index]
        colors = colors[index]

    pcd.points = o3d.utility.Vector3dVector(points)
    pcd.colors = o3d.utility.Vector3dVector(colors)
    return pcd


def create_axis_arrow(size=3.0):
    mesh_frame = o3d.geometry.TriangleMesh.create_coordinate_frame(size=size, origin=[-0, -0, -0])
    return mesh_frame


def view_cloud(pcd, coord, view_params, render_param_file, firstloop=True, video=False, videospeed=0.1):
    vis.add_geometry(pcd)
    vis.add_geometry(coord)
    vis.get_render_option().load_from_json(render_param_file)
    ctr.convert_from_pinhole_camera_parameters(view_params)
    vis.update_geometry(pcd)
    vis.update_geometry(coord)

    if not video:
        print('Press ESC to exit the submap cloud viz')

        def on_press(key, endkey='esc'):
            try:
                k = key.char  # single-char keys
            except:
                k = key.name  # other keys

            if k == endkey:
                print('ending viz ...')
                return False  # stop listener

        def loop_fun():
            while True:
                vis.poll_events()
                vis.update_renderer()
                time.sleep(0.05)

        listener = keyboard.Listener(on_press=on_press)
        listener.start()  # start to listen on a separate thread

        # start thread with loop
        if firstloop:
            t = Thread(target=loop_fun, args=(), name='loop_fun', daemon=True)
            t.start()

        listener.join() # wait for endkey
    else:
        vis.poll_events()
        vis.update_renderer()
        time.sleep(videospeed)

    vis.remove_geometry(pcd)
    vis.remove_geometry(coord)



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--loaddir', default=str(root_dir.parent / 'Wildscenes3d' / 'K-01'),
                        help="Path to directory in WildScenes to read data, for example K-01")
    parser.add_argument('--viewpoint', choices=['BEV', 'FPV'], default='BEV',
                        help="Choice of viewpoints for rendering the labeled 3D point clouds, either birds eye view or first person view")
    parser.add_argument('--loadidx', default=-1, type=int,
                        help="Specify which cloud index you want to view. Defaults to a random cloud from the traverse")
    parser.add_argument('--sequential', default=False, action='store_true',
                        help="Iteratively view all clouds in a traverse, starting from 0 or loadidx")
    parser.add_argument('--video', default=False, action='store_true',
                        help="View the clouds as a continuous video, starting from 0 or loadidx")
    parser.add_argument('--videospeed', default=0.5, type=float,
                        help='Video playback speed, lower is faster')
    args = parser.parse_args()

    cloud_xyz = sorted(glob(os.path.join(args.loaddir, 'Clouds', '*')))
    labels = sorted(glob(os.path.join(args.loaddir, 'Labels', '*')))

    if args.loadidx >= len(labels):
        raise ValueError('Your loadidx is greater than the number of clouds in this traverse')

    if args.viewpoint == 'BEV':
        view_params = o3d.io.read_pinhole_camera_parameters(
            os.path.join(root_dir, 'wildscenes', 'configs', 'viewpoint_bev.json'))
        render_param_file = os.path.join(root_dir, 'wildscenes', 'configs', 'render_bev.json')
    else:
        view_params = o3d.io.read_pinhole_camera_parameters(
            os.path.join(root_dir, 'wildscenes', 'configs', 'viewpoint_fpv.json'))
        render_param_file = os.path.join(root_dir, 'wildscenes', 'configs', 'render_fpv.json')

    vis = o3d.visualization.Visualizer()
    vis.create_window(width=960, height=1080, visible=True)
    ctr = vis.get_view_control()
    coord = create_axis_arrow(1)

    if args.sequential:
        firstloop = True
        if args.loadidx == -1:
            args.loadidx = 0
        for idx in range(args.loadidx, len(labels)):
            if args.viewpoint == 'BEV':
                pcd = load_pcd(cloud_xyz[idx], labels[idx])
            else:
                pcd = load_pcd(cloud_xyz[idx], labels[idx], fpv=True)
            view_cloud(pcd, coord, view_params, render_param_file, firstloop=firstloop)
            firstloop = False

    elif args.video:
        if args.loadidx == -1:
            args.loadidx = 0
        for idx in range(args.loadidx, len(labels)):
            if args.viewpoint == 'BEV':
                pcd = load_pcd(cloud_xyz[idx], labels[idx])
            else:
                pcd = load_pcd(cloud_xyz[idx], labels[idx], fpv=True)
            view_cloud(pcd, coord, view_params, render_param_file, video=True, videospeed=args.videospeed)

    else:
        if args.loadidx == -1:
            args.loadidx = np.random.randint(len(labels))
        if args.viewpoint == 'BEV':
            pcd = load_pcd(cloud_xyz[args.loadidx], labels[args.loadidx])
        else:
            pcd = load_pcd(cloud_xyz[args.loadidx], labels[args.loadidx], fpv=True)

        view_cloud(pcd, coord, view_params, render_param_file)

    print('EXITING')