import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


class read_pos_file:
    def __init__(self, arg,num):
        '''
        input: path to file num is number of chunks
        '''
        self.filename = os.fspath(arg)
        stacked_array = np.vstack([
        np.load(os.path.join(self.filename, f"positions_chunk_{i}.npy"))
        for i in range(num)
        ])
        self.positions_df = pd.DataFrame(stacked_array, columns=['time_stamp', 'x', 'y', 'file'])
        x=np.linspace(0,len(self.positions_df['time_stamp']),len(self.positions_df['time_stamp']))
        y=self.positions_df['time_stamp'].diff()
        plt.xlabel('number of timestamps')
        plt.ylabel('difference between time stamps')
        #plt.ylim(0,100000)
        plt.plot(x,y)
    def stats(self):
        mean_time = self.positions_df['time_stamp'].mean()/self.positions_df['time_stamp'].max()
        print(f"Mean exposure time: {mean_time:.2f} us )")
        #us is cooming from the manual
        print(f"Mean exposure time: {mean_time:.2f} us )")
    def plotts(self):
        """
        Plot a 2D heatmap of (x, y) position frequencies.
        """
        df = self.positions_df
        location_counts = df.groupby(['x', 'y']).size().reset_index(name='counts')

        heatmap_data = location_counts.pivot_table(
            index='y',
            columns='x',
            values='counts',
            fill_value=0
        )

        plt.figure(figsize=(10, 8))
        im = plt.imshow(
            heatmap_data.values,
            cmap='Blues',
            origin='lower',
            extent=[
                heatmap_data.columns.min(), heatmap_data.columns.max(),
                heatmap_data.index.min(), heatmap_data.index.max()
            ],
            aspect='equal'
        )
        cbar = plt.colorbar(im)
        cbar.set_label('Frequency of Appearance', rotation=270, labelpad=15)
        plt.xlabel('X Coordinate')
        plt.ylabel('Y Coordinate')
        plt.title('Heatmap of Unique Positions')
        plt.tight_layout()
        plt.show()
