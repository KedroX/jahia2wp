<?php
require_once __DIR__."/../lib/prometheus.php";


use Prometheus\CollectorRegistry;
use Prometheus\RenderTextFormat;

$adapter = new Prometheus\Storage\APC();

$registry = new CollectorRegistry($adapter);
/* Using custom render class */
$renderer = new EPFLRenderTextFormat();

$result = $renderer->render($registry->getMetricFamilySamples(), ['timestamp']);
header('Content-type: ' . RenderTextFormat::MIME_TYPE);
echo $result;