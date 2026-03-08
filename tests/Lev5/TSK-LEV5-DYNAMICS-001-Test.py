import unittest
import numpy as np
import os
import sys
import json

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))

from dynamics.Boolean_Dynamics import BooleanDynamics
from complexity.Trajectory_LZ import TrajectoryLZ

class TestLev5Dynamics(unittest.TestCase):
    
    def setUp(self):
        # Path to real biological network
        self.net_path = os.path.join(os.path.dirname(__file__), '../../data/bio/processed/ginsim_2006-mammal-cell-cycle_boolean_cell_cycle.json')
        if not os.path.exists(self.net_path):
            self.skipTest("Real network file not found")
            
        with open(self.net_path, 'r') as f:
            self.net_data = json.load(f)
            
        self.dynamics = BooleanDynamics(self.net_data)

    def test_simulation_runs(self):
        """TSK-LEV5-DYNAMICS-001: Simulation Performance & Validity"""
        # Test basic run
        steps = 100
        traj = self.dynamics.simulate(steps=steps, initial_state='random')
        self.assertEqual(traj.shape, (steps + 1, self.dynamics.n))
        
        # Check values are binary
        self.assertTrue(np.all(np.isin(traj, [0, 1])))
        
    def test_attractor_detection(self):
        """TSK-LEV5-DYNAMICS-001: Attractor Convergence"""
        # Biological networks usually have short attractors.
        # Run for longer to settle
        steps = 200
        traj = self.dynamics.simulate(steps=steps, initial_state='random')
        
        # Check if the last state appeared before
        last_state = traj[-1]
        
        found_cycle = False
        # Search backwards from -2
        for i in range(steps-1, -1, -1):
            if np.array_equal(traj[i], last_state):
                found_cycle = True
                cycle_len = steps - i
                print(f"Converged to attractor of length {cycle_len}")
                break
                
        # It's highly likely to find an attractor in 200 steps for N=10
        self.assertTrue(found_cycle, "Failed to converge to an attractor within 200 steps")

    def test_lz_complexity(self):
        """TSK-LEV5-DYNAMICS-002: Lempel-Ziv Complexity"""
        steps = 100
        traj = self.dynamics.simulate(steps=steps, initial_state='random')
        
        lz = TrajectoryLZ.compute_trajectory_lz(traj, method='flatten')
        self.assertGreater(lz, 0)
        
        # Compare with random matrix
        rand_traj = np.random.randint(2, size=traj.shape)
        lz_rand = TrajectoryLZ.compute_trajectory_lz(rand_traj, method='flatten')
        
        print(f"Bio LZ: {lz:.4f}, Random LZ: {lz_rand:.4f}")
        
        # Random trajectory should generally have higher complexity (less compressible)
        # unless Bio is chaotic? But Bio usually ordered.
        self.assertLess(lz, lz_rand, "Biological trajectory should be simpler than random noise")

if __name__ == '__main__':
    unittest.main()
