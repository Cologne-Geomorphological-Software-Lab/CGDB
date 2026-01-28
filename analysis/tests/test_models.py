from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from analysis.models import Algorithm

class AlgorithmTestCase(TestCase):
    def setUp(self):
        test_file = SimpleUploadedFile(
            "test_files/test.txt",
            b"file_content",
            content_type="text/plain"
        )
        Algorithm.objects.create(
            name = "Dijkstra",
            version = "1.0",
            description = "The Dijkstra algorithm calculates the shortest paths in an edge-weighted graph.",
            file = test_file,
            programming_language = "Python"
        ),

    def test_algorithm_file_upload(self):
        dijkstra = Algorithm.objects.get(name="Dijkstra")
        self.assertTrue(dijkstra.file.name.startswith("analysis/algorithms/test"))

    def test_algorithm_fields(self):
        algorithm = Algorithm.objects.get(name="Dijkstra")
        self.assertEqual(algorithm.name, "Dijkstra")
        self.assertEqual(algorithm.version, "1.0")
        self.assertEqual(algorithm.programming_language, "Python")
        self.assertEqual(algorithm.description, "The Dijkstra algorithm calculates the shortest paths in an edge-weighted graph.")
        self.assertTrue(algorithm.file) 