(function(global) {
  
  // map tells the System loader where to look for things
  var map = {
    'rxjs':                       'node_modules/rxjs',
    'angular-in-memory-web-api': 'node_modules/angular-in-memory-web-api',
    '@angular':                   'node_modules/@angular',
    '@angular/router':            'node_modules/@angular/router',
    'angular-cookie':            'node_modules/angular-cookie',
    'primeng':                    'node_modules/primeng',
    'ng2-nvd3':                   'node_modules/ng2-nvd3/build/lib/ng2-nvd3',
  };

  // packages tells the System loader how to load when no filename and/or no extension
  var packages = {
    'rxjs':                       { defaultExtension: 'js' },
    'angular-in-memory-web-api': { defaultExtension: 'js' },
    'angular-cookie':            { main: 'core.js',  defaultExtension: 'js' },
    'primeng':                    { defaultExtension: 'js' },
  };

  var packageNames = [
    '@angular/common',
    '@angular/compiler',
    '@angular/core',
    '@angular/forms',
    '@angular/http',
    '@angular/platform-browser',
    '@angular/platform-browser-dynamic',
    '@angular/router',
    '@angular/testing',
    '@angular/upgrade'
  ];

  // add package entries for angular packages in the form '@angular/common': { main: 'index.js', defaultExtension: 'js' }
  packageNames.forEach(function(pkgName) {
    packages[pkgName] = { main: 'index.js', defaultExtension: 'js' };
  });

  var config = {
    defaultJSExtensions: true,
    map: map,
    packages: packages
  }

  // filterSystemConfig - index.html's chance to modify config before we register it.
  if (global.filterSystemConfig) { global.filterSystemConfig(config); }

  System.config(config);

})(this);