var argv         = require('minimist')(process.argv.slice(2));
var autoprefixer = require('gulp-autoprefixer');
var cache        = require('gulp-cached');
var concat       = require('gulp-concat');
var gulp         = require('gulp');
var gulpif       = require('gulp-if');
var livereload   = require('gulp-livereload');
var plumber      = require('gulp-plumber');
var rename       = require('gulp-rename');
var sass         = require('gulp-sass');
//var sourcemaps   = require('gulp-sourcemaps');
var uglify       = require('gulp-uglify');

var enabled = {
		failCheck: argv.production,
		maps: argv.production,
		uglify: argv.production
};


/* CSS */
gulp.task('styles', function() {
	gulp
		.src('src/styles/**/*.sass')
		.pipe(gulpif(enabled.failCheck, plumber()))
		//.pipe(gulpif(enabled.maps, sourcemaps.init()))
		.pipe(sass({outputStyle: 'compressed'}))
		.pipe(autoprefixer("last 3 versions"))
		//.pipe(gulpif(enabled.maps, sourcemaps.write(".")))
		.pipe(gulp.dest('dillo/static/css'))
		.pipe(gulpif(argv.livereload, livereload()));
});


/* Individually uglified scripts */
gulp.task('scripts', function() {
    gulp.src('src/scripts/*.js')
        .pipe(gulpif(enabled.failCheck, plumber()))
        .pipe(cache('scripting'))
        //.pipe(gulpif(enabled.maps, sourcemaps.init()))
        .pipe(gulpif(enabled.uglify, uglify()))
        .pipe(rename({suffix: '.min'}))
        //.pipe(gulpif(enabled.maps, sourcemaps.write(".")))
        .pipe(gulp.dest('dillo/static/js/generated/'))
        .pipe(gulpif(argv.livereload, livereload()));
});


/* Collection of scripts in src/scripts/tutti/ to merge into tutti.min.js */
/* Since it's always loaded, it's only for functions that we want site-wide */
gulp.task('scripts_tutti', function() {
    gulp.src('src/scripts/tutti/**/*.js')
        .pipe(gulpif(enabled.failCheck, plumber()))
        //.pipe(gulpif(enabled.maps, sourcemaps.init()))
        .pipe(concat("tutti.min.js"))
        .pipe(gulpif(enabled.uglify, uglify()))
        //.pipe(gulpif(enabled.maps, sourcemaps.write(".")))
        .pipe(gulp.dest('dillo/static/js/generated/'))
        .pipe(gulpif(argv.livereload, livereload()));
});


/* Simple task for reloading the browser */
gulp.task('reload', function(){
	gulp
		.src('dillo/templates/**/*.pug')
		.pipe(gulpif(argv.livereload, livereload()));
});


// While developing, run 'gulp watch'
gulp.task('watch',function() {
	// Only reload the pages if we run with --livereload
	if (argv.livereload){
		livereload.listen();
		// Templates are built via python, we only need to reload the page
		gulp.watch('dillo/templates/**/*.pug',['reload']);
	}

	gulp.watch('src/styles/**/*.sass',['styles']);
	gulp.watch('src/scripts/*.js',['scripts']);
	gulp.watch('src/scripts/tutti/*.js',['scripts_tutti']);
});


// Run 'gulp' to build everything at once
gulp.task('default', ['styles', 'scripts', 'scripts_tutti']);
