import yaml
from pycirclize import Circos
from IPython.display import Image, display
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
import os
import numpy as np

class DecisionCalendar:
    def __init__(self, config_path='ross.yaml'):
        # Load configuration
        self.config = self._load_config(config_path)

        # Define colors from config
        self.colors = self._parse_colors(self.config['colors'])

        # Define month ranges and sectors
        self.month_ranges = self.config['month_ranges']
        self.sectors = self.config['sectors']

        # Define track configurations
        self.track_configs = self.config['track_configs']

        # Define legend groups
        self.legend_groups = self.config['legend_groups']

        # Define plot settings
        self.plot_settings = self.config['plot_settings']

    def _load_config(self, path):
        """Load YAML configuration file."""
        with open(path, 'r') as file:
            config = yaml.safe_load(file)
        return config

    def _parse_colors(self, colors_config):
        """Parse colors from configuration."""
        parsed_colors = colors_config  # Already structured as nested dict
        print("Parsed Colors:", parsed_colors)  # Debugging line
        return parsed_colors

    def _get_color(self, color_key):
        """Retrieve color from parsed colors using the full key."""
        keys = color_key.split('.')
        color = self.colors
        for key in keys:
            if isinstance(color, dict) and key in color:
                color = color[key]
            else:
                raise ValueError(f"Color key '{color_key}' not found in configuration.")
        if isinstance(color, str):
            return color
        else:
            raise ValueError(f"Color key '{color_key}' does not resolve to a color string.")

    def _add_track(self, sector, track_config):
        """Add tracks to sectors based on configuration."""
        # Get sector's month
        sector_month = sector.name

        if sector_month in track_config.get('months', []):
            if track_config.get('type') == "infill":
                # Add infill (filled sector) using track.rect
                track = sector.add_track((track_config['r_start'], track_config['r_end']))
                
                # Define angular range as the full sector (0 to sector.size)
                angular_start = 0
                angular_end = sector.size
                
                # Define radial range
                radial_start = track_config['r_start']
                radial_end = track_config['r_end']
                
                # Add rectangle (infill) with r_lim as keyword argument
                try:
                    track.rect(
                        angular_start,    # start_angle (positional)
                        angular_end,      # end_angle (positional)
                        r_lim=(radial_start, radial_end),  # r_lim (keyword)
                        facecolor=self._get_color(track_config['color']),
                        edgecolor='none',
                        alpha=track_config.get('alpha', 1.0),
                        zorder=1  # Set lower zorder for lines
                    )
                    print(f"Added infill: {track_config['color']} to sector: {sector_month}")  # Debugging
                except TypeError as e:
                    print(f"Error adding infill track: {e}")
                    raise

            elif track_config.get('type') == "arrow":
                # Add arrow track
                track = sector.add_track((track_config['r_start'], track_config['r_end']))
                track.arrow(
                    start=0,
                    end=sector.size,
                    shaft_ratio=0.3,
                    head_length=0,
                    fc=self._get_color(track_config['color']),
                    ec=self._get_color(track_config['color']),
                    alpha=0.7,
                    linestyle=track_config.get('linestyle', '-'),
                    linewidth=track_config.get('linewidth', 1),
                    zorder=1  # Set lower zorder for lines
                )
                print(f"Added arrow: {track_config['color']} to sector: {sector_month}")  # Debugging
                
            elif track_config.get('type') == "line":
                # Add line track
                track = sector.add_track((track_config['r_start'], track_config['r_end']))
                track.line(
                    x=[0, sector.size],
                    y=[track_config['r_start'], track_config['r_start']],
                    vmin=track_config['r_start'],
                    vmax=track_config['r_end'],
                    color=self._get_color(track_config['color']),
                    linestyle=track_config.get('linestyle', '-'),
                    linewidth=track_config.get('linewidth', 1),
                    zorder=1  # Set lower zorder for lines
                )
            elif track_config.get('type') == "marker":
                # Add marker track
                point = track_config['r_points'][sector.name]
                print(f"Adding marker to sector: {sector.name} at {point}")
                track = sector.add_track((point-2, point))
                track.scatter(
                    [track_config['position']],
                    [point],
                    vmin=point-2,
                    vmax=point,
                    s=track_config.get('s', 200),
                    color=self._get_color(track_config['color']),
                    marker=track_config['marker'],
                    linewidth=track_config.get('linewidth', 1),
                    zorder=5
                )
    def create_plot(self, center_image=None):
        """Create the circular decision calendar plot."""
        figsize = self.plot_settings['figsize']['plot']

        # Initialize Circos plot
        circos = Circos(
            sectors=self.sectors,
            space=0,
            start=0,
            end=360
        )

        # Plot sectors
        for sector in circos.sectors:
            # Setup sector
            sector.axis(fc="none", ec="grey", alpha=0.5, zorder=0)  # Background lines
            sector.text(sector.name, size=15, r=26, zorder=3)  # Ensure text is on top

            # Add tracks based on configurations
            for config_name, track_config in self.track_configs.items():
                if isinstance(track_config, list):
                    for cfg in track_config:
                        self._add_track(sector, cfg)
                else:
                    self._add_track(sector, track_config)
            if center_image is not None:
                sector.raster(center_image, r=0, size=0.15)

        # Create figure
        fig = circos.plotfig(figsize=figsize)
        
        # Add legend
        self._add_legend(fig)

        #plt.tight_layout()
        return fig

    def _add_legend(self, fig):
        """Add a multi-column legend to the figure based on configuration."""
        legend_groups = self.legend_groups
        legends = []

        # Iterate over each group to create separate legend handles
        for group_name, group in legend_groups.items():
            group_handles = []
            group_labels = []

            # Add group header without fontsize and fontweight
            header = f"{group_name.replace('_', ' ')}:"
            group_handles.append(Line2D([], [], 
                                        label=header, 
                                        color='none'))
            group_labels.append(header)

            # Add group elements
            for element in group['elements']:
                # Handle space elements
                if element.get('type') == 'space':
                    group_handles.append(Line2D([], [], color='none', label=' '))
                    group_labels.append(' ')
                    continue
                    
                elem_type = element['type']
                color_key = element['color']
                color = self._get_color(color_key)
                label = element['label']
                
                if elem_type == 'patch':
                    handle = Patch(facecolor=color, alpha=0.5, label=label)
                elif elem_type == 'line':
                    linestyle = element.get('linestyle', '-')
                    linewidth = element.get('linewidth', 1)
                    handle = Line2D(
                        [0], [0],
                        color=color,
                        linestyle=linestyle,
                        linewidth=linewidth,
                        label=label
                    )
                elif elem_type == 'arrow':
                    linestyle = element.get('linestyle', '-')
                    linewidth = element.get('linewidth', 1)
                    handle = Line2D(
                        [0], [0],
                        color=color,
                        linestyle=linestyle,
                        linewidth=linewidth,
                        label=label
                    )
                elif elem_type == 'marker':
                    marker = element.get('marker', 'o')
                    markersize = element.get('markersize', 10)
                    linewidth = element.get('linewidth', 1)
                    handle = Line2D(
                        [0], [0],
                        marker=marker,
                        color=color,
                        linestyle='None',
                        markersize=markersize,
                        markeredgewidth=linewidth,
                        label=label
                    )
                group_handles.append(handle)
                group_labels.append(label)
            
            legends.append((group_handles, group_labels))

        # Number of legend columns
        ncols = len(legends)

        # Positioning parameters
        bbox = self.plot_settings['legend']['bbox']  # [x, y]
        legend_width = 1.0 / ncols

        # Create each legend separately and position them side by side
        for i, (handles, labels) in enumerate(legends):
            # Define the position of each legend column
            ax_legend = fig.add_axes([
                bbox[0] + i * legend_width,  # x-position
                bbox[1],                    # y-position
                legend_width,               # width
                0.1                         # height
            ])
            ax_legend.axis('off')  # Hide the axes

            # Create the legend
            legend = ax_legend.legend(
                handles=handles,
                labels=labels,
                loc='upper left',
                frameon=True,
                facecolor=self.plot_settings['legend']['facecolor'],
                edgecolor=self.plot_settings['legend']['edgecolor'],
                fontsize=self.plot_settings['legend']['fontsize'],
                handletextpad=0.5,
                columnspacing=1.0,
                handlelength=1.5,
                alignment='left'
            )

            # Customize header text (first label)
            for text in legend.texts:
                if text.get_text().endswith(':'):
                    text.set_fontsize(self.plot_settings['legend']['title_fontsize'])
                    text.set_fontweight('bold')

        # Adjust the main figure to make space for the legends
        fig.subplots_adjust(bottom=0)  # Adjust as needed
    
    def save_plot(self, fig, filename, dpi=1000, bbox_inches='tight', pad_inches=0.1):
        """Save the figure to a file."""
        fig.savefig(filename, dpi=dpi, bbox_inches=bbox_inches, pad_inches=pad_inches)



# Example usage
if __name__ == "__main__":
    calendar = DecisionCalendar(config_path='../config/chena.yaml')
    center_image = ('../images/alaska_outline.png')

    # Create and save the decision calendar plot
    fig = calendar.create_plot(center_image=center_image)
    calendar.save_plot(fig,'../output/chena_decision_calendars.png')
