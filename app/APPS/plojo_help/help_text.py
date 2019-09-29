

topic_key = ['toprow','ubfbutton','infobox','editbutton','plotbutton','loadsavebutton',
'uploadlayout','uploadoptions','browselayout','tabs','search','editinfo','fittinglayout','curvefit',
'simuojo','howtosimuojo','fitmethod','howfit','supportedfitmodel','confidence']

text_dict = dict.fromkeys(topic_key,'Nothing Yet')




#'>>> Top Row Buttons <<<'
text_dict['toprow'] = """<h2>Top Row Buttons</h2>
<img src="plojo_help/static/toprow.png" alt="top row" height='39' width="800">
<h3>Top row buttons located at top of screen, consist of 3 elements.</h3>
<p><b>Mode Selection Button</b>: switching between layouts.<p>
<p><b>Information Box</b>: display plojo prompts.<p>
<p><b>Tool bar</b>: buttons offer some frequently used functions.<p>
"""

# '+---- Upload/Browse/Fitting Button
text_dict['ubfbutton'] = """<h2>Upload/Browse/Fitting Button</h2>
<img src="plojo_help/static/ubfbutton.png" alt="ubfbutton" height='49' width="201">
<p> Click on these buttons switches between the below interface layouts. </p>
<p> <b>Upload layout</b> is for uploading data only. </p>
<p> <b>Browse layout</b> is for browsing data, editing data info such as Name/Tag/Assay Type/Flag/Note etc. This is the only place you can delete data.</p>
<p> <b>Fitting layout</b> is for view and change fitting methods / fitting parameter boundary, mark outliers, then fit based on new parameters. Can also reset fitting parameters.</p>
<div style="width:100%; height:30px" ></div>
"""

# info box
text_dict['infobox'] ="""<h2>Information Box</h2>
<img src="plojo_help/static/infobox.png" alt="info box" height='52' width="400">
<p><b>Information box</b> is located between Upload/Browse/Fitting buttons and Edit button.</p>
<p>Last 3 of plojo feedback messages are displayed here.</p>
<h3>Pay attention to it when using plojo, it can help catch some abnormal behaviors.</h3>
"""

# Edit Button
text_dict['editbutton'] ="""<h2>Edit Button</h2>
<p><b>Edit button</b> have four main functions.</p>
<img src="plojo_help/static/editbutton.png" alt="edit button" hspace='20' align='right' height='252' width="150">
<h3>Copy Fit Para/Paste Fit Para</h3>
<p>They are used to copy fitting parameters from one experiment and paste to other experiments.</p>
<p>To use, select <b>one experiment data</b> in the Experiment or To Plot tab, click Copy Fit Para, the fitting parameter will be copied.</p>
<p>Then select one or multiple experiment data, click Paste Fit Para to paste the fitting parameters.</p>
<p><b>Tips:</b> The copied parameters will remain in the memory if you didn't copy another data. So you can select different data and paste the same parameters multiple times.
<h3>Alias/Merge Data</h3>
<p>Combine with <b>"Key:AND/OR/NOT/ANY | Enter Alias"</b> input box, this is used to create an copy of a selected data, or merge a group of selected data into one experiment.</p>
<p>To <b>copy a data</b>, select 1 experiment in Experiment or To Plot tab, enter a new name in the "Key:AND/OR/NOT/ANY | Enter Alias" input box. Then click Alias/Merge Data to create a copy with the entered new name affix.</p>
<p>To <b>Merge a group of data</b>, select multiple experiment in the Experiment or To Plot tab, enter a new name, and click the button. All the selected data will be Combined into 1 experiment, and plojo will be using all the combined data for fitting and R squared and Confidence Intervals calculations.</p>
<p><b>Caution: </b>If no name was entered, by default "copy" will be added as a default alias to distinguish original data and the copy.</p>
<h3>Cut / Copy / Paste Data</h3>
<p>Combine with <b>Project / Experiment / To Plot Tab</b>, they can be used to move experiment data around in the project foler. </p>
<p>To use,  </p>
<p>1.Select one or multiple data you want to migrate in the Experiment or To Plot Tab.</p>
<p>2.Click <b>Cut Data </b> if you want to <b>move </b>the experiment data from one project folder to another. </p>
<p>2.Click <b>Copy Data </b> if you want to <b>create copies</b> of experiment data in another project folder. </p>
<p>3.Select the project folder you want to migrate the data in <b>Project Tab</b>, then click <b>Paste Data</b>.  </p>
<h3>Check Consistency / Align Index</h3>
<p>Rarely, the index of experiment data may not match the stored data. Thus some data might not be displayed in the data list, or some data entry doesn't contain any actual data.</p>
<p>Click <b>Check Consistency</b>, plojo will find mismatches of indexes and data, display the result in Information box. </p>
<p>Click <b>Align Index</b>, plojo will attempt to remove the 'bad' indexes and re-create index for some data that doesn't have a matching index. </p>
<div style="width:100%; height:30px" ></div>
"""

# Plot Button
text_dict['plotbutton'] ="""<h2>Plot Button</h2>
<p><b>Plot button</b> is for adjusting plot options and mark outlier in the data.</p>
<img src="plojo_help/static/plotbutton.png" alt="plot button" hspace='20' align='right' height='241' width="150">
<h3>Mark Outlier</h3>
<p>To mark outlier in experiment data,</p>
<p>1.Make sure only <b>1 data curve</b> is being selected in the <b>To Plot tab</b> and only <b>1 curve</b> is being plotted.</p>
<p>2.Select the data point(s) you want to mark as outlier in the <b>Raw Data tab</b>.</p>
<p><b>Tips:</b> You use hover tool on the raw data point in the plot to find out X value of data.</p>
<p><b>Caution:</b> The values displayed in Raw Data tab is only for the experiment selected in <b>To Plot tab</b>, and will only show up when 1 selection is made. It <b style="color:red;">will not mark outlier</b> for curves selected in the Experiment Tab!</p>
<p>3.Click <b>Mark Outlier</b>. A cross will be displayed in overlay with outlier.</p>
<p>4.Click <b>Fit and Plot</b> button in the <b>Fitting layout</b>. New fitting will be performed excluding selected outliers.</p>
<p><b>Caution:</b> If you don't click Fit and Plot button, simply marking outlier won't have effect and won't be saved even if you click the Save button!</p>
<h3>Show / Hide 95% CI</h3>
<p>Toggle between show/hide the band overlay of <a href="https://en.wikipedia.org/wiki/Confidence_interval"><b>95% confidence intervals</b><a>. Default: show </p>
<p>The confidence interval overlay can be annoying if you are plotting multiple curves.</p>
<h3>X-axis Linear / Log Scale</h3>
<p>Toggle between linear and log X-axis scale.</p>
<h3>Plot in SVG / PNG format</h3>
<p>Toggle between using SVG / PNG picture format for the plots. Default: PNG format</p>
<p> <a href="https://en.wikipedia.org/wiki/Scalable_Vector_Graphics"><b>Scalable Vector Graphics (SVG)</b></a> is an XML-based vector image format for two-dimensional graphics.</p>
<p><a href="https://en.wikipedia.org/wiki/Portable_Network_Graphics"><b>Portable Network Graphics (PNG)</b></a> is a raster-graphics file-format that supports lossless data compression. </p>
<div style="width:100%; height:30px" ></div>

"""

# Load/Save Button
text_dict['loadsavebutton'] ="""<h2>Load/Save Button</h2>
<p><b>Load/Save button</b> is for re-load the data into plojo and save the edits you make to server.</p>
<img src="plojo_help/static/loadsavebutton.png" alt="loadsavebutton" hspace='20' align='center' height='50' width="244">
<h3>Load Button</h3>
<p>Potential using scenario: </p>
<p><b>Mistakes:</b> if some terrible mistakes happened, you can re-load data to abort those unsaved changes.</p>
<p><b>Use with Simuojo:</b> if plojo is opened, after saving data to plojo from simuojo, the newly simulated data won't show up. Use load button to force re-load.</p>
<h3>Save Button</h3>
<p><b>Save your changes!!!</b></p>
<p>Even some operations may automatically invoke saving, most of the curve fitting operations and info changes won't.  If you don't click the Save button, <b>all your efforts will be gone</b> after closing plojo.</p>
<h1 style="color:red;">Click That Save Button!</h1>
<p><b>Tips:</b> Any <b style="color:red;">red colored button</b> will invoke saving data onto server. All other buttons only changes data in memory, <b>will not write</b> data to server.</p>
<div style="width:100%; height:30px" ></div>

"""

# '>>> Upload Data <<<'
text_dict['uploadlayout'] ="""<h2>Upload layout</h2>
<p> <b>Upload layout</b> is for uploading data only. </p>
<img src="plojo_help/static/uploadlayout.png" alt="uploadlayout" hspace='20' align='center' height='448' width="700">
<p><h3>Brief Precedure for Uploading Data</h3></p>
<p><b>Author / Experiment Data</b> are loaded automatically, from the login user name and current date.</p>
<p>Choose your <b>Assay Type</b>. The assay type you choose here <b style="color:red;">determines the default Fit Method</b> after the data was loaded. Select the right assay type here will save you some trouble!</p>
<p>Paste your data from "plojo_template" to Experiment Data field.</p>
<p><b>Select the project folder</b> you want to upload the data to in the Project List. By default, it is set to temporary folder. For creating new project folder, refer to "Project/Experiment... Tabs".</p>
<p>Click <b>Read Input Data</b>. The pasted data will be format checked and loaded in the table for view. Check if the data in the table is indeed what you are expecting.</p>
<p>Click <b>Save Input Data</b> to save the data.</p>
<div style="width:100%; height:30px" ></div>

"""


# '+---- Upload Data Options'
text_dict['uploadoptions'] ="""<h2>Other options to Upload data</h2>
<p>In addition to pasting formatted data to plojo, you can upload an .csv file.</p>
<p>Make sure use the .csv template with <b>utf16</b> in its name. The same formating rules also apply here.</p>
<p>After uploading the .csv file, data will be displayed in the table. You <b style="color:red;">should not click</b> <b>Read Input Data</b>. </p>
<p>Review the data and click <b>Save Input Data </b>to save.</p>
"""


# '>>> Browse Data <<<'
text_dict['browselayout'] ="""<h2>Browse layout</h2>
<p> <b>Browse layout</b> is for browsing data, editing data info such as Name/Tag/Assay Type/Flag/Note etc. This is the only place you can delete data.</p>
<img src="plojo_help/static/browse.png" alt="browse" hspace='20' align='center' height='568' width="800">
<h3>Plotting Area</h3>
<p><b>Raw Data and Normalized</b> plots are displayed here.</p>
<h3>View Plot Toolkit</h3>
<p>A group of widgets to facilitate viewing plot.</p>
<p>Tools include:</p>
<p><b>Pan, Box Zoom, X-Wheel Zoom, Y-Wheel Zoom</b>: Move the curve around, Zoom in the selected are, or zoom along X/Y axis.</p>
<p><b>Save</b>: Save the displayed plot. Selected plot formats apply.</p>
<p><b>Reset</b>: Reset both the pan and zoom to default setting.</p>
<p><b>Hover Tooltip</b>: click to select which hover tools are active. There are 2 type of hover tips: 1. display raw x/y data; 2. display curve fitting result and tag.</p>
<h3>Delete Data Button</h3>
<p>This is the only place you can <b style="color:red;">delete an experiment data</b>.</p>
<p>Select the experiment(s) you want to delete in <b>Experiment</b> or <b>To Plot</b> tab, then <b style="color:red;">double click</b> the button to delete data.</p>
<p>After deletion, data will be gone in the experiment list. But it is not delete from server until <b>save button (or any button in red)</b> is clicked. If you deleted data by mistake, you can use <b>Load</b> button to reload the data back immediately.</p>
<h3>Save Info Button</h3>
<p>Save experiment information changes you made in the <b>Experiment Info</b> area.</p>
<h3>External Functions/Help Doc</h3>
<p>Starts <b>simuojo</b> or this help document.</p>
<h3>Project Experiment Tab</h3>
<p>Refer to <b>Project/Experiment... Tabs</b> topic for details.</p>
<h3>Search Box</h3>
<p>Refer to <b>plojo Keyword Search</b> topic for details.</p>
<h3>Experiment Info</h3>
<p>Refer to <b>Edit/Save Experiment Information</b> topic for details.</p>
<div style="width:100%; height:30px" ></div>

"""

# '+---- Project/Experiment... Tabs'
text_dict['tabs'] ="""<h2>Project/Experiment/To Plot/Raw Data/Fitting Result Tabs</h2>
<p><b></b></p>
<img src="plojo_help/static/tabs.png" alt="tabs" hspace='20' align='center' height='234' width="500">
<h3>Project tab</h3>
<p>Select one or multiple projects, the experiments in the selected projects will be shown in Experiment tab.<b>Recent Upload</b> folder contain 50 most recently uploaded experiments.</p>
<p>To <b>create, rename or delete</b> a project: </p>
<p>1. Enter the new name in <b>Project Name</b> input box. If rename project, select that project.</p>
<p>2. Click 'Edit Project' -> 'New Project' to create project, or 'Rename Project' to rename.</p>
<p>3. Select project folder, then click 'Edit Project' -> 'Delete Project' to delete.</p>
<p><b>Tips:</b> If a project contains experiments, after deleting the project, all contained experiments will be moved to temporary folder.</p>
<h3>Experiment/To Plot tab</h3>
<p>Select experiments in experiment tab. Selected experiments will be shown in To Plot tab. Experiments selected in To Plot tab will be plotted.</p>
<p><b>Caution</b>:To avoid clutter, when selecting data to plot in the To Plot tab, only first 10 selected data will be plotted. However, fitting result will still be displayted.
<p>Whenever <b>a new selection is made</b> in either Experiment or To Plot tab, the experiment info of newly selected experiments will be displayed in Experiment Info box, the fitting result will be displayed in Fitting Result tab.</p>
<h3>Raw Data tab</h3>
<p>Raw data of experiment will be displayed here only if <b>single experiment was selected in To Plot</b> tab.</p>
<h3>Fitting Result tab</h3>
<p>Display fitting result of selected experiment in either Experiment or To Plot tab, depends on where the last selection was made.</p>
<div style="width:100%; height:30px" ></div>

"""


# '+---- plojo Keyword Search'
text_dict['search'] ="""<h2>plojo Keyword Search</h2>
<img src="plojo_help/static/search.png" alt="browse" hspace='15' align='right' height='280' width="230">
<h3>Scope of the Search</h3>
<p>Searching scope is within the Project(s) you selected. That is, only experiments shown in the Experiment tab will be searched. Select multiple or all projects in the Project tab to expand searching scope.</p>
<h3>Search Filters:</h3>
<p><b>Asssay Type Filter:</b> select 1 or multiple assay type will filter out experiments of other type. </p>
<p><b>Keyword Filter:</b> Enter the keyword(s) you want to search. Supported Logic Operators are AND/OR/NOT/ANY, detailed below.</p>
<h3>Search Field</h3>
<p>Since each experiment data has its "Name, Date, Tag, Flag, Note, Author, Fitmethod" fields, select the field(s) you want to perform keyword search.</p>
<h3>Search / Refine Button</h3>
<p>To perform a <b>new search</b> with the specified "Assay Type/Keywords/Search field" in the current search scope, click <b>Search</b>. The number of hits will be displayed in Information Box. Search hits are shown in the Experiment Tab.</p>
<p>To futher search using keywords within the currently shown search result, type in the keyword and select Search Field, then click <b>Refine</b> button. This will perform a keyword search within the previous searching result.</p>
<p>To <b>clear the search result</b> and show all experiments in selected projects, you can either: 1. refresh the project selection in the Project tab; or 2. perform a blank search by selecting all Assay Types, leave keyword blank, and click Search button.</p>
<h3>Supported Logic Operators</h3>
<p>If no logic operator is used, plojo will search for an <b>exact match</b> of the pharase you entered. That is, use 'ice cream' as keyword will hit results contain 'apple ice cream cup', but not 'apple icecream cup' or 'apple ice-cream cup'. However, the match is <b style="color:red;">not case sensitive</b>. That is, 'ICE' will hit 'ice' or 'iCe' or 'Ice'.</p>
<p>When use them, operators must be <b stype="color:red">CAPTIALIZED</b>. Currently, you can only use 1 operator type at a time.</p>
<p><b>AND</b>: search for result that contain all phrases connected by AND. For example:</p>
<p>apple AND banana AND ice cream : will hit results contain 'apple', 'banana', 'ice cream' at the same time.</p>
<p><b>OR</b>: search for result that contain any phrases connected by OR. For example:</p>
<p>apple OR banana OR ice cream : will hit results contain either 'apple', 'banana' or 'ice cream'.</p>
<p><b>NOT</b>: search for result that contain pharase before NOT and doesn't contain phrases after NOT. The phrase before NOT is optional. For example:</p>
<p>NOT strawberry icecream : will hit results that doesn't have 'strawberry icecream', but will still hit results that contain 'strawberry' or 'icecream' at separated places.</p>
<p>apple icecream NOT strawberry icecream : will hit results that contain 'apple icecream' but not 'strawberry icecream'.</p>
<p><b>ANY</b>: search for result that contain any words after ANY. It is similar to connecting each work with OR. For example:</p>
<p>ANY apple ice cream: search for result that contain either 'apple' or 'ice' or 'cream'. This equals: apple OR ice OR cream.</p>
<div style="width:100%; height:30px" ></div>

"""


# '+---- Edit/Save Experiment Information'
text_dict['editinfo'] ="""<h2>Browse layout</h2>
<img src="plojo_help/static/data_info.png" alt="datainfo" hspace='20' align='right' height='388' width="230">
<p>Whenever a new selection is made in <b>either Experiment or To Plot</b> tab, the experiment info of newly selected experiments will be displayed in respective fields.</p>
style="color:red;"
<h3>Edit Experiment Info</h3>
<p>Type new information in the field you want to change. then click the <b>Save Info</b> button.</p>
<img src="plojo_help/static/infoedit.png" alt="datainfo" hspace='20' align='bottom' height='30' width="187">
<p><b>Caution:</b> When you click <b>Save Info</b> button, all the text in the filed that you have made changes, will be saved to all currently selected experiments. When multiple experiments is selected, their information are all shown in the same field and separated by ','. When you edit them, delete all text and enter new. If you want to edit individual experiemnt info, select only 1 experiment then continue.</p>
<p><b>Caution:</b> To save edited information, you need to click <b>Save Info</b> button. The <b>Save</b> button in Top Row will not save information changes you made.</p>
<p><b>Tips:</b> The Flag field is a good place to categorize or group data that are related, and will be helpful for future search purpose.</p>
<div style="width:100%; height:30px" ></div>

"""

# '>>> Fitting Data <<<'
text_dict['fittinglayout'] ="""<h2>Fitting layout</h2>
<p> <b>Fitting layout</b> is for view and change fitting methods / fitting parameter boundary, mark outliers, then fit based on new parameters. Can also reset fitting parameters.</p>
<img src="plojo_help/static/fitlayout.png" alt="browse" hspace='20' align='bottom' height='551' width="750">
<p>Whenever <b>a new selection is made</b> in either Experiment or To Plot tab, the fit method and fitting parameter boundaries of newly selected experiments will be displayed in <b>Fitting Parameter Box</b>, the fitting result will be displayed in Fitting Result tab.</p>
<div style="width:100%; height:30px" ></div>

"""

# '+---- Curve Fitting with plojo'
text_dict['curvefit'] ="""<h2>Curve Fitting with plojo</h2>
<img src="plojo_help/static/fittinginfo.png" alt="browse" hspace='20' align='right' height='316' width="230">
<h3>Perform Fitting</h3>
<p>By default, after you uploaded the data, plojo alread determined a Fitting Method based on the Assay-Type. Whenever you select an newly uploaded experiment in To Plot tab, plojo will use the pre-loaded fit method and default fitting parameter to perform a curve fit and display plot. However, sometimes the default parameter may not give the best result. You will need to manually adjust fitting parameters.</p>
<h3>Manual Adjustment of Fitting Parameters</h3>
<p>1. To start, select the data you want to fit in <b>To Plot tab</b>.</p>
<p><b>Caution:</b> Even though selection in Experiment Tab will also display their fitting parameter in Fitting Parameter Box, changing fitting parameter in Fitting Parameter Box and perform new fit only affect data selected in To Plot tab. Make sure you are on the <b>To Plot</b> tab when performing new fitting.</p>
<p>2. Select a proper <b>Fitting Method</b>. Refer to Fitting Methods topic for details.</p>
<p>3. The available fitting parameter are shown in the Fitting Parameter Box. Type in the new boundary in the format of 10-1000, or 1e3-5e3. if you need to type negative values, use ':' instead of '-' to separate upper and lower boundary. For example, use 1e-3:1e3 or -100:100.</p>
<p>If multiple data are selected, and they are using the same Fitting Method, their fitting parameter boundaries will all be displayed and separated by ','. Changes will apply to all selected data. If you enter only 1 boundary, this boudary will be applied to all selected data.</p>
<p>You can change individual data boundaries by keep the ',' and others untouched. Or type in multiple boundaries and separate them by ','. Plojo is able to correctly understand multiple boundaries separated by ','.</p>
<p>4. Mark outliers in Raw Data tab, click Plot -> Mark Outlier.</p>
<p>5. Click <b>Fit and Plot</b> button to use new fitting parameter for fit.</p>
<div style="width:100%; height:30px" ></div>

"""

# '>>> Simuojo <<<'
text_dict['simuojo'] ="""<h2>Simuojo</h2>
<h3>Purpose of Simuojo</h3>
<p>Simuojo is used to simulate signal curve with predetermined model, then use simulated data to evaluate fitting process.</p>
<h3>Simuojo Access</h3>
<p>To launch simuojo, click <b>External Functions/Help Doc</b> -> <b>Simuojo</b> in Browse layout.</p>
<img src="plojo_help/static/simuojoaccess.png" alt="simuaccess" hspace='20' align='center' height='109' width="250">
<p>Simuojo will be opened in a new browser window.</p>
"""

# '+---- How to use simuojo?'
text_dict['howtosimuojo'] ="""<h2>How to Use Simuojo</h2>
<img src="plojo_help/static/simuojolayout.png" alt="simuojo" hspace='20' align='center' height='553' width="600">
<h3>Select a Simulation model</h3>
<p>First select a model you want to simulate.</p>
<p>The selected model options and model formula will be displayed.</p>
<h3>Change Model Parameters</h3>
<p>Use silder to change simulating parameters.</p>
<p><b>Binding parameters</b> Slider for changing parameters in the model, such as Kd or concentration.</p>
<p><b>Randomization Parameters</b> Slider for changing simulation options. Linear Randomization is adding a normal distributed random signal to datapoints. Proportional Randomization is adding a normal distributed random signal proportional to original signal of each datapoint.</p>
<p><b>Refresh Random Data</b> Click the button will refresh the random seed used to generate randomization.</p>
<h3>Add data to plojo</h3>
<p><b>Enter a name </b>for the simulated data.</p>
<p>Export data to plojo by click the <b>Add data to plojo</b> button.</p>
<p>Load data in plojo.</p>
<p>Exported simulation data will be in plojo under 'simuojo data' project folder.</p>
<div style="width:100%; height:30px" ></div>

"""

# '>>> Fitting Methods <<<'
text_dict['fitmethod'] ="""<h2>Fitting methods</h2>
<p>Plojo performs both <a href='https://en.wikipedia.org/wiki/Nonlinear_regression'><b>Nonlinear regression</b><a>
and <a href=https://en.wikipedia.org/wiki/Linear_regression><b>linear regression</b><a>.</p>
<h3>Currently Supported Fitting Models</h3>
<img src="plojo_help/static/fitmethod.png" alt="browse" hspace='20' align='center' height='186' width="300">
<h3>Which Model to Use?</h3>
<p>Your goal in using a model is not necessarily to describe your system perfectly. A perfect model may have too many parameters to be useful. Rather, your goal is to find as simple a model as possible that comes close to describing your system. You want a model to be simple enough so you can fit the model to data, but complicated enough to fit your data well and give you parameters that help you understand the system and design new experiments.</p>
<p>You can also use a model to simulate data, and then analyze the simulated data. This can help you design better experiments.</p>
<p>Two interesting quotations about models:<p>
<blockquote> <i>"A mathematical model is neither an hypothesis nor a theory. Unlike scientific hypotheses, a model is not verifiable directly by an experiment. For all models are both true and false.... The validation of a model is not that it is "true" but that it generates good testable hypotheses relevant to important problems. “</i>  -- R. Levins, Am. Scientist 54:421-31, 1966</blockquote>
<blockquote> <i>“All models are wrong, but some are useful.”   </i>-- George E. P. Box</blockquote>
<div style="width:100%; height:30px" ></div>

"""


# how fitting
text_dict['howfit']="""<h2>How Does Fitting Work?</h2>
<p>Plojo use non-linear least squares to fit a function Y = f(X,B1,B2...) to data.</p>
<p>The method of least squares minimizes the error sum of squares, Q, which is given by:</p>
<img src="plojo_help/static/residual.png" alt="resid" hspace='20' align='center' height='60' width="136">
<p>where Y^ is the value predicted for a specific Xi using the parameters B1,B2... estimated by least squares. If the errors are normally distributed, the least squares estimates are also the maximum likelihood estimates.</p>
<p>The values of the parameters that minimize Q may be found either of two ways. First, if f() is a simple function, such as a linear function, you may find an analytic solution by differentiating Q with respect to B1, B2, ..., Bp, setting the resulting partial derivatives equal to zero, and solving the resulting p normal equations. Unfortunately, very few nonlinear models may be estimated this way.</p>
<p>The second method is to try different values for the parameters, calculating Q each time, and work towards the smallest Q possible. Three general procedures work toward a solution in this manner.</p>
<p>Plojo use a specific algorithm implementation of the second method called <a href='https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.least_squares.html#scipy.optimize.least_squares'>Trust Region Reflective (trf)<a> method.</p>
<h3>Fitting of a noisy curve</h3>
<img src="plojo_help/static/fitting_.gif" alt="resid" hspace='20' align='center' height='300' width="400">
<p>Fitting of a noisy curve by an asymmetrical peak model, with an iterative process (Gauss–Newton algorithm with variable damping factor α). Top: raw data and model. Bottom: evolution of the normalised sum of the squares of the errors.</p>
<div style="width:100%; height:30px" ></div>

"""
# '+---- Supported Fitting Models'
text_dict['supportedfitmodel'] ="""<h2>Supported Fitting Models</h2>
<h3>Kd measurement related models</h3>
<img src="plojo_help/static/kdformula.png" alt="browse" hspace='20' align='center' height='235' width="450">
<h3>IC50 curve and Dose Response Curve 4/5 Parameter Logistic Curve</h3>
<img src="plojo_help/static/ec50.png" alt="browse" hspace='20' align='center' height='171' width="400">
<p>For the Dose Response Curve 4/5 Parameter Logistic Curve, Hill coefficient determine steepness of the curve at EC50 point. Symmetry factor determine the asymmetrical shape of curve around EC50 point.</p>
<p><b>Tips:</b> For the Dose Response curves, Fmax is not necessarily larger than Fmin. So it can be used to fit both a rising curve (Kd curve) or decreasing curve (IC50 curve). The resulted EC50 is still valid, you just need to replace Fmax and Fmin. </p>
<h3>RIC 50 Curve</h3>
<img src="plojo_help/static/ric50.png" alt="browse" hspace='20' align='center' height='58' width="400">
<p>Ric50 fitting using starting [V]0, [R]0 concentration and Kdr Kda as parameter, calculating free [RV] concentration at any starting aptamer concentration, then use this function to find best parameters.</p>
<p>Due to the fact that 1. There are many paramters to fit (Total of 6 including Fmax and Fmin), 2. Parameters are not orthogonal, different parameter combinations can give very similar curve. The fitting is hard to converge and often yield bad confidence interval for fitted parameters.</p>
<h3>Linear Fit</h3>
<p>The formula for linear fit is simply Y = slope * X + b </p>
<h3>Plojo Default boundaries</h3>
<p>By default, plojo use a fixed rule to determine boundaries for each paramter.</p>
<p>For fluorescence signal Fmax, Fmin, the default boundary is 0 to 2e6.</p>
<p>For any paramter that use nM as its unit, the defalt boundary is 1e-3 to 1e5; or 1pM to 100uM.</p>
<p>For Hill: default boundary is 0.01-2. For Symmetry coefficient, default boundary is 0.1-10.</p>
<p>For slope and intercept, defalt boundary is 1e-6 to 1e6.</p>
<div style="width:100%; height:30px" ></div>

"""

# '+---- Confidence Intervals'
text_dict['confidence'] ="""<h2>Confidence Intervals</h2>
<p> The 95% CI is supposed to be an interval that has a 95% chance of containing the true value of the parameter. More precisely, if you perform nonlinear regression many times (on different data sets) you expect the confidence interval to include the true value 95% of the time, but to exclude the true value the other 5% of the time (but you won't know when this happens).</p>
<h3>How asymptotic standard errors are computed.</h3>
<p>Check <a href="https://en.wikipedia.org/wiki/Confidence_interval">This page</a> for some basic information.</p>
<p>The basic step of calculating confidence interval of a curve fit parameter have 2 steps.</p>
<p>1.<b>Calculate standard errors of each paramter.</b> Each standard error is calculated from 3 terms:</p>
<p>The first term is the hardest to calculate. At each value of X, compute how much the predicted value of Y changes if you change the value of each parameter a little bit from its best fit value (compute dY/dA, where A is a parameter and Y is computed from your model holding each parameter fixed to its best-fit value). Combine all these together into a matrix and do some heavy-duty matrix manipulations to obtain a value that depends on the model, the parameters, the number of data points, and the values of X. Note that this value is not influenced at all by the scatter of your data.</p>
<p>The sum-of-squares of the vertical distances of the data points from the curves. Or simply put, the variance of residuals. This quantifies how scattered the data are.</p>
<p>The number of degrees of freedom, computed as the number of data points minus the number of parameters.</p>
<p>2.<b>Determine confidence interval</b>, from best fit paramter value, standard error and find inverse of t-distribution from two tailed t-distribution table using 95% criteria and degrees of freedom. Use following equation to calculate the interval.</b></p>
<img src="plojo_help/static/cicalc.png" alt="browse" hspace='20' align='center' height='20' width="200">
<p>If you have plenty of degrees of freedom (more than a dozen or so) t* will have a value near 2.0.</p>
<div style="width:100%; height:30px" ></div>
"""
