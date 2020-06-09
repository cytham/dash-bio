"""
VariantMap plot

Author: CY THAM

Version: 1.0.0
"""

import math
import numpy as np
import pandas as pd

import plotly.graph_objects as go


def VariantMap(
        dataframe,
        entries_per_batch=2500,
        batch_no=1,
        annotation=None,
        filter_sample=None,
        filter_file=None,
        sample_order=None,
        title='',
        sample_names=None,
        color_list=None,
        colorbar_thick=25,
        rangeslider=True,
        height=500,
        width=600
):
    """Returns a Dash Bio VariantMap figure.

Keyword arguments:

- dataframe (dataframe; required): A pandas dataframe generated by VariantBreak.
    Please pre-process your VCF files with VariantBreak and load the output object here.
- entries_per_batch (number; default 2500): Number of SV entries to display
    in a batch.
- batch_no (number; default 1): Batch number to display in the plot.
    SVs are grouped by batches and the batches are labeled numerically and
    chronologically with descending SV prevalence. Only a single batch is
    allowed to be displayed in an instance, unless a slider is used in an app
    to switch between each batch. Number of total batches = total number of
    SV entries / entries_per_batch, rounded up.
- annotation (dict; optional): A dictionary where the keys are annotation
    labels and the values are list of respective annotations. Only SVs with
    the selected annotations will be displayed in the plot. The keys are:
    'Gene_id', 'Transcript_id', 'Gene_name', 'Gene_type' and 'Gene_feature'
    for GTF/GFF. For BED annotation files, the key will be their 4th column
    label if present, or else they will be 'BED1', 'BED2' and so on. Please
    refer to the legend.txt file.
- filter_sample (list; optional): The list of default sample names
    (e.g. 'S1', 'S2') to be removed from the plot together with the SVs they
    possessed. For example, a non-diseased sample can be selected by this
    argument to omit non-diseased associated SVs in the remaining diseased sample.
- filter_file (list; optional): The list of default filter names
    (e.g. 'Filter1', 'Filter2') for filter activation. SVs that overlapped with
    the respective filter BED files will be excluded from the plot.
- sample_order (list, optional): The list of default sample names
    (e.g. 'S1', 'S2') with the order intended for plotting. Samples can also be
    omitted from the plot using this argument.
- title (string; optional): Title of plot.
- sample_names (dict; optional): If provided, sample labels will follow this
    dict rather than the default labels (e.g. 'S1', 'S2') extracted from the
    VariantBreak object. The keys should be: 'S1', 'S2', 'S3' and so on,
    depending on how many samples you have.
- color_list (dict; optional): The list of colors to use for different SV classes.
    The keys are: 'DEL' (deletion), 'INV' (inversion), 'INS' (insertion),
    'BND' (translocation or transposition), 'DUP' (tandem duplication), 'UKN' (unknown),
    'NIL' (SV not detected).
- colorbar_thick (number; optional): The thickness of the colorbar, in px.
- rangeslider (bool; default True): Whether or not to show the range slider.
- height (number; default 500): The height of the graph, in px.
- width (number; default 700): The width of the graph, in px.


Usage example:

import pandas as pd
import dash_bio

# Load dataframe and metadata
file_path = "/path/to/sample.h5"
with pd.HDFStore(file_path, mode="r") as store:
    df = store['dataset']
    metadata = store.get_storer('dataset').attrs.metadata

# Add metadata to dataframe
df.metadata = ''
df.metadata = data['metadata']

# Plot VariantMap
fig = dash_bio.VariantMap(df)

    """

    # Get labels of samples to display
    if sample_order is None:
        samples = dataframe.metadata['sample_names']  # All samples to be displayed and default order
    else:
        samples = sample_order

    sv_classes = ['NIL', 'DEL', 'INV', 'INS', 'BND', 'DUP', 'UKN']

    color_dict = {'DEL': '#4daf4a',
                  'INV': '#377eb8',
                  'INS': '#e41a1c',
                  'BND': '#984ea3',
                  'DUP': '#ff7f00',
                  'UKN': '#000000',
                  'NIL': '#d1d9e0'}

    colors = []

    # Generate color list for colorbar
    if color_list is None:
        for _class in sv_classes:
            colors.append(color_dict[_class])
    else:
        for _class in sv_classes:
            try:
                colors.append(color_list[_class])
            except KeyError:
                colors.append(color_dict[_class])

    vm = _VariantMap(
        dataframe,
        entries_per_batch,
        batch_no,
        annotation,
        filter_sample,
        filter_file,
        title,
        samples,
        sample_names,
        colors,
        colorbar_thick,
        rangeslider,
        height,
        width
    )

    return vm.figure()


class _VariantMap:

    """Returns a Dash Bio VariantMap object.

Methods:

- figure: Returns a VariantMap plotly graph object.
    """

    def __init__(
            self,
            df,
            entries_per_batch,
            batch_no_for_display,
            annotation,
            filter_sample,
            filter_file,
            title,
            samples,
            sample_names,
            colors,
            colorbar_thick,
            rangeslider,
            height,
            width
    ):
        self.title = title
        self.colorbar_thick = colorbar_thick
        self.rangeslider = rangeslider
        self.height = height
        self.width = width

        # Generating discrete colorscale
        markers = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4]
        self.dcolorsc = discrete_colorscale(markers, colors)
        self.tickvals = [0.071, 0.214, 0.357, 0.500, 0.643, 0.786, 0.929]
        self.ticktext = ['NIL', 'DEL', 'INV', 'INS', 'BND', 'DUP', 'UKN']

        # Subset dataframe by gene name and SV index
        if annotation:
            if 'Gene_name' in annotation and 'index_list' in annotation:
                if annotation['Gene_name'] and annotation['index_list']:
                    df_genes = df[df['Gene_name'].str.contains('|'.join([x + ';' for x in annotation['Gene_name']]))].copy()
                    df_indexes = df.loc[annotation['index_list'], :].copy()
                    df = pd.concat([df_genes, df_indexes])
                else:
                    if annotation['Gene_name']:
                        df = df[df['Gene_name'].str.contains('|'.join([x + ';' for x in annotation['Gene_name']]))]
                    if annotation['index_list']:
                        df = df.loc[annotation['index_list'], :]
            else:
                if 'Gene_name' in annotation:
                    if annotation['Gene_name']:
                        df = df[df['Gene_name'].str.contains('|'.join([x + ';' for x in annotation['Gene_name']]))]
                if 'index_list' in annotation:
                    if annotation['index_list']:
                        df = df.loc[annotation['index_list'], :]

        # Subset dataframe by annotation
        if annotation:
            for _key in annotation:
                if annotation[_key]:
                    if _key in ['Gene_name', 'index_list']:
                        pass
                    else:
                        df = df[df[_key].str.contains('|'.join(annotation[_key]))]

        # Subset dataframe by sample filter
        if filter_sample:
            for sample in filter_sample:
                df = df[df[sample] == 0.0]

        # Subtset dataframe by filter file
        if filter_file:
            for _filter in filter_file:
                df = df[df[_filter] != '1']

        # Make a copy of dataframe
        df_new = df.copy()

        # Get actual sample order list
        sample_order = [x for x in samples if x in df_new.columns]

        # Calculate number of divisions
        div = math.ceil(len(df_new) / entries_per_batch) + 0.001

        # Calculate actual batch size
        self.batch_size = math.ceil(len(df_new) / div)

        # Add batch number to dataframe
        df_new.loc[:, 'Group'] = np.divmod(np.arange(len(df_new)), self.batch_size)[0] + 1

        # Subset dataframe by batch label
        df_new = df_new[df_new['Group'].isin([int(batch_no_for_display)])]

        # Transpose dataframe
        df_new = df_new.T

        # Subset sample rows from dataframe and convert to list of lists
        z = df_new.loc[sample_order, :].values.tolist()

        # Reverse list
        self.z = z[::-1]

        # Subset hover-text row from dataframe and convert to list of lists
        hover_list = ['Hover_' + x for x in sample_order]
        hover_text = df_new.loc[hover_list, :].values.tolist()

        # Reverse list
        self.hover = hover_text[::-1]

        # Change sample labels if provided
        if sample_names is None:
            names = sample_order
        else:
            names = []
            for name in sample_order:
                try:
                    names.append(sample_names[name])
                except KeyError:
                    names.append(name)

        # Reverse sample name list
        names.reverse()
        self.names = names

    def figure(self):
        """
        :return: a go.Figure object
        """
        trace1 = go.Heatmap(
            z=self.z,
            y=self.names,
            colorscale=self.dcolorsc,
            colorbar=dict(
                title=dict(
                    text='SV classes',
                    font=dict(
                        family='Open Sans',
                        size=14,
                        color='#ffffff'
                    )
                ),
                thickness=self.colorbar_thick,
                tickvals=self.tickvals,
                ticktext=self.ticktext,
                tickfont=dict(
                    family='Open Sans',
                    size=14,
                    color='#ffffff'
                )
            ),
            zmin=0.0,
            zmax=1.0,
            hovertext=self.hover,
            hoverinfo='text',
            xgap=2,
            ygap=2

        )

        layout = go.Layout(
            title=dict(
                text='<b>' + self.title + '<b>',
                font=dict(
                    family='Open Sans',
                    size=18,
                    color='#ffffff'
                ),
                x=0.48
            ),
            xaxis=dict(
                title=dict(
                    text='Variants',
                    font=dict(
                        family='Open Sans',
                        size=16,
                        color='#ffffff'
                    ),
                    standoff=3
                ),
                rangeslider=dict(
                    visible=self.rangeslider
                ),
                showticklabels=False,
                side='top',
                type='-',
            ),
            yaxis=dict(
                title=dict(
                    text='Samples',
                    font=dict(
                        family='Open Sans',
                        size=16,
                        color='#ffffff'
                    ),
                    standoff=3
                ),
                tickfont=dict(
                    family='Open Sans',
                    size=14,
                    color='#ffffff'
                )
            ),
            height=self.height,
            width=self.width,
            paper_bgcolor='rgba(10,43,77,255)',
            plot_bgcolor='rgba(255,255,255,255)'
        )

        return go.Figure(data=[trace1], layout=layout)


def discrete_colorscale(markers, colors):
    """
    :param markers:
    :param colors:
    :return: color scale
    """
    markers = sorted(markers)
    norm_mark = [round((v - markers[0]) / (markers[-1] - markers[0]), 3) for v in markers]
    dcolorscale = []
    for k in enumerate(colors):
        dcolorscale.extend([[norm_mark[k[0]], colors[k[0]]], [norm_mark[k[0] + 1], colors[k[0]]]])
    return dcolorscale
