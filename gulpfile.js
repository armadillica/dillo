let pillar       = '../pillar/';
let pillarMod    = pillar + 'node_modules/';

let argv         = require(pillarMod + 'minimist')(process.argv.slice(2));
let autoprefixer = require(pillarMod + 'gulp-autoprefixer');
let cache        = require(pillarMod + 'gulp-cached');
let concat       = require(pillarMod + 'gulp-concat');
let gulp         = require('gulp');
let gulpif       = require(pillarMod + 'gulp-if');
let pug          = require(pillarMod + 'gulp-pug');
let livereload   = require(pillarMod + 'gulp-livereload');
let plumber      = require(pillarMod + 'gulp-plumber');
let rename       = require(pillarMod + 'gulp-rename');
let sass         = require(pillarMod + 'gulp-sass');
let sourcemaps   = require(pillarMod + 'gulp-sourcemaps');
var uglify       = require(pillarMod + 'gulp-uglify-es').default;

var enabled = {
		failCheck: !argv.production,
		maps: !argv.production,
		prettyPug: !argv.production,
		uglify: argv.production
};

var source = {
		pillar: '../pillar/'
};

/* Stylesheets */
gulp.task('styles', function(done) {
	gulp
		.src('src/styles/**/*.sass')
		.pipe(gulpif(enabled.failCheck, plumber()))
		.pipe(gulpif(enabled.maps, sourcemaps.init()))
		.pipe(sass({outputStyle: 'compressed'}))
		.pipe(autoprefixer("last 3 versions"))
		.pipe(gulpif(enabled.maps, sourcemaps.write(".")))
		.pipe(gulp.dest('dillo/static/css'))
		.pipe(gulpif(argv.livereload, livereload()));
	done();
});


/* Templates */
gulp.task('templates', function(done) {
	gulp.src('src/templates/**/*.pug')
		.pipe(gulpif(enabled.failCheck, plumber()))
		.pipe(cache('templating'))
		.pipe(pug({
			pretty: enabled.prettyPug
		}))
		.pipe(gulp.dest('dillo/templates/'))
		.pipe(gulpif(argv.livereload, livereload()));
	done();
});


/* Individually uglified scripts */
gulp.task('scripts', function(done) {
	gulp.src('src/scripts/*.js')
		.pipe(gulpif(enabled.failCheck, plumber()))
		.pipe(cache('scripting'))
		.pipe(gulpif(enabled.maps, sourcemaps.init()))
		.pipe(gulpif(enabled.uglify, uglify()))
		.pipe(rename({suffix: '.min'}))
		.pipe(gulpif(enabled.maps, sourcemaps.write(".")))
		.pipe(gulp.dest('dillo/static/js/generated/'))
		.pipe(gulpif(argv.livereload, livereload()));
	done();
});


/* Collection of scripts in src/scripts/tutti/ to merge into tutti.min.js */
/* Since it's always loaded, it's only for functions that we want site-wide */
gulp.task('scripts_tutti', function(done) {
	gulp.src('src/scripts/tutti/**/*.js')
		.pipe(gulpif(enabled.failCheck, plumber()))
		//.pipe(gulpif(enabled.maps, sourcemaps.init()))
		.pipe(concat("tutti.min.js"))
		.pipe(gulpif(enabled.uglify, uglify()))
		//.pipe(gulpif(enabled.maps, sourcemaps.write(".")))
		.pipe(gulp.dest('dillo/static/js/generated/'))
		.pipe(gulpif(argv.livereload, livereload()));
	done();
});


// While developing, run 'gulp watch'
gulp.task('watch',function(done) {
	// Only reload the pages if we run with --livereload
	if (argv.livereload){
		livereload.listen();
	}

	let watchStyles = [
		'src/styles/**/*.sass',
		source.pillar + 'src/styles/**/*.sass',
	];

	let watchTemplates = [
		'src/templates/**/*.pug',
		source.pillar + 'src/templates/**/*.pug',
	];

	gulp.watch(watchStyles, gulp.series('styles'));
	gulp.watch(watchTemplates, gulp.series('templates'));

	gulp.watch('src/scripts/*.js',gulp.series('scripts'));
	gulp.watch('src/scripts/tutti/*.js',gulp.series('scripts_tutti'));
	done();
});


// Run 'gulp' to build everything at once
gulp.task('default', gulp.parallel('styles', 'templates', 'scripts', 'scripts_tutti'));
