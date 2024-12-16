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
    def __init__(self, config_path='ross.yaml', 
                 streamflow_csv=None, 
                 swe_csv=None):
        # Load configuration
        self.config = self._load_config(config_path)

        # Define colors from config
        self.colors = self._parse_colors(self.config['colors'])

        # Define month ranges and sectors
        self.month_ranges = self.config['month_ranges']
        # Update sectors to match number of days per month
        self.sectors = self._generate_sectors(self.month_ranges)

        # Define track configurations
        self.track_configs = self.config['track_configs']

        # Define legend groups
        self.legend_groups = self.config['legend_groups']

        # Define plot settings
        self.plot_settings = self.config['plot_settings']

        if streamflow_csv is not None:
            self.streamflow_data = self._load_and_process_data(streamflow_csv, value_col='discharge', date_col='datetime')
        else:
            self.streamflow_data = None

        if swe_csv is not None:
            self.swe_data = self._load_and_process_data(swe_csv, value_col='swe', date_col='datetime')
        else:
            self.swe_data = None

    def _load_config(self, path):
        """Load YAML configuration file."""
        with open(path, 'r') as file:
            config = yaml.safe_load(file)
        return config

    def _parse_colors(self, colors_config):
        """Parse colors from configuration."""
        parsed_colors = colors_config
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

    def _generate_sectors(self, month_ranges):
        # month_ranges is a dict {Month: [start_day, end_day]}
        # We will create a sectors dict {Month: number_of_days}
        sectors = {}
        for month, days in month_ranges.items():
            start_day, end_day = days
            num_days = end_day - start_day + 1
            sectors[month] = num_days
        return sectors
    
    def _load_and_process_data(self, csv_file, value_col, date_col='datetime'):
        df = pd.read_csv(csv_file, parse_dates=[date_col])
        df['day_of_year'] = df[date_col].dt.dayofyear

        def percentile_func(x, q):
            x_clean = x.dropna()
            return np.percentile(x_clean, q) if len(x_clean) > 0 else np.nan

        grouped = df.groupby('day_of_year')[value_col]
        daily_stats = grouped.agg(
            mean='mean',
            p10=lambda x: percentile_func(x, 10),
            p90=lambda x: percentile_func(x, 90)
        )

        daily_stats = daily_stats.fillna(0)

        max_val = daily_stats['p90'].max()
        if max_val == 0:
            max_val = 1.0

        daily_stats['mean_scaled'] = daily_stats['mean'] / max_val
        daily_stats['p10_scaled'] = daily_stats['p10'] / max_val
        daily_stats['p90_scaled'] = daily_stats['p90'] / max_val

        data_dict = daily_stats.to_dict('index')
        return data_dict

    def _scale_data(self, series, max_val):
        # Scale data to fit into a predefined radial range later
        # Actual scaling will be handled during plotting according to track r_start, r_end
        # Here we just normalize from 0 to 1
        return series / max_val if max_val != 0 else series

    def _add_track(self, sector, track_config):
        """Add tracks to sectors based on configuration."""
        sector_month = sector.name
        if sector_month in track_config.get('months', []):
            ttype = track_config.get('type')

            if ttype in ["infill", "arrow", "line", "marker"]:
                self._add_static_track(sector, track_config)
            elif ttype == "data_plot":
                if track_config['data_type'] == 'streamflow' and self.streamflow_data is not None:
                    self._add_data_plot(sector, track_config)
                elif track_config['data_type'] == 'swe' and self.swe_data is not None:
                    self._add_data_plot(sector, track_config)
                else:
                    print(f"No data available for {track_config['data_type']}.")
    
    def _add_static_track(self, sector, track_config):
        """Add static (existing) track types: infill, arrow, line, marker."""
        ttype = track_config.get('type')
        sector_month = sector.name
        if ttype == "infill":
            track = sector.add_track((track_config['r_start'], track_config['r_end']))
            track.axis()
            track.rect(
                0, sector.size,
                r_lim=(track_config['r_start'], track_config['r_end']),
                facecolor=self._get_color(track_config['color']),
                edgecolor='none',
                alpha=track_config.get('alpha', 1.0),
                zorder=1
            )
        elif ttype == "arrow":
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
                zorder=1
            )
        elif ttype == "line":
            track = sector.add_track((track_config['r_start'], track_config['r_end']))
            track.line(
                x=[0, sector.size],
                y=[track_config['r_start'], track_config['r_start']],
                vmin=track_config['r_start'],
                vmax=track_config['r_end'],
                color=self._get_color(track_config['color']),
                linestyle=track_config.get('linestyle', '-'),
                linewidth=track_config.get('linewidth', 1),
                zorder=1
            )
        elif ttype == "marker":
            # Marker at a specific radial point defined in config
            point = track_config['r_points'][sector_month]
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

    def _add_data_plot(self, sector, track_config):
        data_type = track_config['data_type']
        data = self.streamflow_data if data_type == 'streamflow' else self.swe_data

        r_start = track_config['r_start']
        r_end = track_config['r_end']
        color_mean = self._get_color(track_config['color_mean'])
        color_env = self._get_color(track_config['color_envelope'])

        start_day, end_day = self.month_ranges[sector.name]
        num_days = end_day - start_day + 1

        track = sector.add_track((r_start, r_end))
        track.axis()

        xs = np.arange(num_days)
        mean_vals, p10_vals, p90_vals = [], [], []

        for day_of_year in range(start_day, end_day+1):
            if day_of_year in data:
                mean_scaled = data[day_of_year]['mean_scaled']
                p10_scaled = data[day_of_year]['p10_scaled']
                p90_scaled = data[day_of_year]['p90_scaled']
            else:
                # If no data, default to zero
                mean_scaled = p10_scaled = p90_scaled = 0.0

            mean_vals.append(mean_scaled)
            p10_vals.append(p10_scaled)
            p90_vals.append(p90_scaled)

        mean_vals = np.array(mean_vals)
        p10_vals = np.array(p10_vals)
        p90_vals = np.array(p90_vals)

        track.fill_between(xs, p10_vals, p90_vals, fc=color_env, alpha=0.6, edgecolor='none', zorder=2, vmin=0, vmax=1)
        track.line(xs, mean_vals, color=color_mean, linewidth=2, zorder=3, vmin=0, vmax=1)

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
            sector.axis(fc="none", alpha=0.5, zorder=0)
            sector.text(sector.name, size=15, r=20, zorder=6)  # Ensure text is on top

            # Add tracks based on configurations
            for config_name, track_config in self.track_configs.items():
                if isinstance(track_config, list):
                    for cfg in track_config:
                        self._add_track(sector, cfg)
                else:
                    self._add_track(sector, track_config)

            if center_image is not None:
                sector.raster(center_image, r=0, size=0.15)

        # Create figurex
        fig = circos.plotfig(figsize=figsize)

        # Add legend
        self._add_legend(fig)

        return fig

    def _add_legend(self, fig):
        """Add a vertical legend to the right side of the figure."""
        legend_groups = self.legend_groups
        all_handles = []
        all_labels = []

        # Combine all legend groups into single lists
        for group_name, group in legend_groups.items():
            # Add group header
            header = f"{group_name.replace('_', ' ')}"
            if 'color' in group:
                color = self._get_color(group['color'])
                header_handle = Line2D([], [], 
                                    marker='s',
                                    color='none',
                                    markerfacecolor=color,
                                    markersize=15,
                                    label=header)
            else:
                header_handle = Line2D([], [], label=header, color='none')
            all_handles.append(header_handle)
            all_labels.append(header)

            # Add group elements
            for element in group['elements']:
                if element.get('type') == 'space':
                    all_handles.append(Line2D([], [], color='none', label=' '))
                    all_labels.append(' ')
                    continue

                elem_type = element['type']
                color_key = element['color'] if 'color' in element else None
                color = self._get_color(color_key) if color_key else 'black'
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
                all_handles.append(handle)
                all_labels.append(label)

        # Create a single axes for the legend on the right side
        ax_legend = fig.add_axes([0.8, 0.1, 0.15, 0.8])
        ax_legend.axis('off')

        legend = ax_legend.legend(
            bbox_to_anchor=(0.1, 1),
            handlelength=2,
            handles=all_handles,
            labels=all_labels,
            loc='upper left',
            frameon=True,
            facecolor=self.plot_settings['legend']['facecolor'],
            edgecolor=self.plot_settings['legend']['edgecolor'],
            fontsize=self.plot_settings['legend']['fontsize'],
            handletextpad=0.5,
            columnspacing=1.0,
            alignment='left'
        )

        # Customize header text (group names)
        for text in legend.texts:
            # Convert group name back to underscore form and check if it exists in legend_groups
            if text.get_text().replace(' ', '_') in legend_groups:
                text.set_fontsize(self.plot_settings['legend']['title_fontsize'])
                text.set_fontweight('bold')

        fig.subplots_adjust(right=0.75)  # Adjust main plot to accommodate legend on the right

    def save_plot(self, fig, filename, dpi=1000, bbox_inches='tight', pad_inches=0.1):
        fig.savefig(filename, dpi=dpi, bbox_inches=bbox_inches, pad_inches=pad_inches)


# Example usage
if __name__ == "__main__":
    calendar = DecisionCalendar(config_path='../config/chena.yaml', 
                                streamflow_csv='../data/Chena_Near_Two_Rivers_streamflow.csv', 
                                swe_csv='../data/Chena_Monument_Creek.csv')
    center_image = ('../images/alaska_outline.png')

    # Create and save the decision calendar plot
    fig = calendar.create_plot(center_image=center_image)
    calendar.save_plot(fig,'../output/chena_decision_calendars.png')