<html>
<head>
    <title>StratusLab Monitor</title>
    <link rel='stylesheet' href='/css/stratuslab.css' type='text/css'>
    %(meta)s
</head>

<body>
    <div class='Page'>
        <div class='Banner'></div>
        <div id='header'>
            <h1>Web Monitor</h1>
        </div>
        <div id='actions'>
            <a href='nodelist.py'>Nodes</a>
            <a href='vmlist.py'>Instances</a>
        </div>
        <div id='refresh'>
            %(autoRefreshLink)s
        </div>
        <div class='Main'>  
            <h2>%(title)s</h2>
%(list)s
            <div class='Footer'>
StratusLab is co-funded by the European Community's<br/>
Seventh Framework Programme (Capacities)<br/>
Grant Agreement INSFO-RI-261552
            </div>
        </div>
    </div>
</body>
<html>
